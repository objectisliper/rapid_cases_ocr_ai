"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import cv2
import config
import pickle
import imutils
import numpy as np
import pytesseract


class StatefulObject(object):
    def __init__(self):
        self.state_file = getattr(self.Meta, 'state_file', 'state.obj')

    def save(self):
        with open(self.state_file, 'wb') as output:
            pickle.dump(self, output, pickle.HIGHEST_PROTOCOL)

    def restore(self):
        ret = None
        with open(self.state_file, 'rb') as state:
            ret = pickle.load(state)

        return ret


class ImagePreprocessing(object):
    """
    Class to preprocess images for better classification
    and object detection
    """

    @staticmethod
    def adjust_gamma(image, gamma=1.0):
        inv_gamma = 1.0 / gamma
        table = np.array([
            ((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)
        ]).astype("uint8")
        return cv2.LUT(image, table)

    @staticmethod
    def exaggerate(image):
        # exaggerates regions of interest
        image = image[..., 2]  # - image[..., 1] - image[..., 2]
        ret, image = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
        return image

    @staticmethod
    def highlight(image):
        # hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_red = np.array([150, 150, 150])
        upper_red = np.array([255, 255, 255])

        mask = cv2.inRange(image, lower_red, upper_red)
        res = cv2.bitwise_and(image, image, mask=mask)

        return res


class KeyFrameFinder(StatefulObject):
    """
    Class that contains methods to find a keyframe
    (steady frame where selection is over and no
    or almost no motion is present)
    """

    class Meta:
        state_file = './trained/keyframefinder.obj'

    def __init__(self, motion_threshold=0.5, skip_frames=10,
                 object_detection_threshold=0.5):
        self.threshold = motion_threshold
        self.skip_frames = skip_frames
        self.object_detection_threshold = object_detection_threshold

        self.templates = {}

        super(KeyFrameFinder, self).__init__()

    def load_template(self, name, template_data):
        # loads new template into self.templates
        # no additional preprocessing as for now
        self.templates[name] = template_data

    def motion_data(self, video_handler):
        # extracts motion data from open video_handler
        # in the form of (x-motion, y-motion, has_single_motion)
        ret = []
        prev_frame, has_prev = None, False
        while (True):
            res, frame = video_handler.read()
            if not res:
                break

            frame = np.float32(frame[..., 0])

            if has_prev:
                diff = cv2.phaseCorrelate(prev_frame, frame)
                has_single_motion = diff[1] > self.threshold
                print(diff)
                ret.append((int(diff[0][0]), int(diff[0][1]), has_single_motion))
            else:
                has_prev = True

            prev_frame = frame

            for i in range(self.skip_frames):
                video_handler.read()

        return ret

    def select_keyframe(self, motion_data, video_handler):
        # selects keyframe based on motion_data and video_handler video data and
        # returns keyframe image
        has_cursor = []
        cursor = self.templates.get('cursor', None)
        if not cursor.any():
            raise Exception('No cursor training data found')

        cursor_in, ic, prev_posx = 0, 0, 0
        prev_frame, has_prev = None, False
        while (True):
            res, frame = video_handler.read()
            if not res:
                break

            # frame = ImagePreprocessing.exaggerate(frame)

            if not has_prev:
                prev_frame = frame
                has_prev = True
                continue

            ic += 1
            object_loc = self.find_object(frame, cursor)
            if object_loc:
                if abs(prev_posx - object_loc[1]) > 0:
                    prev_posx = object_loc[1]
                    cursor_in += 1
            else:
                if cursor_in > 3:
                    # we had cursor appearing and then it disappeared
                    # so here is our keyframe
                    return frame, True
                cursor_in = 0

            prev_frame = frame

            for i in range(self.skip_frames):
                video_handler.read()

        return None, False

    def _has_exception(self, some_text):
        some_text = some_text.lower().strip()
        if 'error' in some_text or 'exception' in some_text or 'failed' in some_text:
            return True
        return False

    def select_keyframe2(self, motion_data, video_handler):
        cursor = self.templates.get('cursor', None)
        if not cursor.any():
            raise Exception('No cursor training data found')

        while (True):
            res, frame = video_handler.read()
            if not res:
                break

            object_loc = self.find_object(frame, cursor)
            if object_loc:
                print('Loc found')
                rtext = pytesseract.image_to_string(frame[..., 0])
                if self._has_exception(rtext):
                    return frame, True

            for i in range(self.skip_frames):
                video_handler.read()

        return None, False

    def find_object(self, target_image, template_image, canny=True):
        # finds object described by template_image on image
        # described by target_image
        if canny:
            gray = cv2.Canny(
                cv2.cvtColor(target_image, cv2.COLOR_BGR2GRAY),
                100,
                200
            )
            template = template_image
            # template = cv2.Canny(template_image, 100, 200)
        else:
            gray = ImagePreprocessing.exaggerate(target_image)
            template = template_image

        # cv2.imshow('Keyframe', template)
        # cv2.waitKey()
        # cv2.destroyAllWindows()
        (iH, iW) = gray.shape[:2]

        object_found = False
        object_loc = None
        current_max = 0.0

        for scale in np.linspace(0.1, 2.0, 50)[::-1]:
            resized = imutils.resize(
                template, width=int(template.shape[1] * scale)
            )

            if resized.shape[0] > iH or resized.shape[1] > iW:
                break

            res = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            delta = 0
            if max_val != 0:
                delta = abs((abs(max_val) - abs(min_val)) / abs(max_val))

            print(f'Checking scale {scale}, max {delta}')

            if delta > self.object_detection_threshold:
                # object found
                print(f'Found at size {scale}, loc {max_loc}')
                object_found = True

                if delta > current_max:
                    current_max = delta
                    object_loc = max_loc

                # show it
                # top_left = max_loc
                # bottom_right = (top_left[0] + 50, top_left[1] + 50)
                # cv2.rectangle(gray, top_left, bottom_right, (255,255,255),3)

                # cv2.imwrite('res.png', gray)

                # cv2.imshow('Keyframe', gray)
                # cv2.waitKey()
                # cv2.destroyAllWindows()
                # return max_loc

        if object_found:
            print(f'MAX: {current_max}')
            top_left = object_loc
            bottom_right = (top_left[0] + 50, top_left[1] + 50)
            cv2.rectangle(gray, top_left, bottom_right, (255, 255, 255), 3)

            cv2.imwrite('res.png', gray)
            return object_loc

        return None

    def extended_find_object(self, target_image, template_image, threshold=40):
        # finds object described by template_image on image
        # described by target_image using scale/rotation/shift invariant
        # features
        gray = cv2.cvtColor(target_image, cv2.COLOR_BGR2GRAY)
        star = cv2.FeatureDetector_create("STAR")
        brief = cv2.DescriptorExtractor_create("BRIEF")

        keypoints_target = star.detect(gray, None)
        keypoints_template = star.detect(template_image, None)

        keypoints_target, des1 = brief.compute(gray, keypoints_target)

        print(des1)

        # bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        # matches = bf.match(des1, des2)

        # store all the good matches as per Lowe's ratio test.
        # good_matches = []
        # for m,n in matches:
        #    if m.distance < 0.7 * n.distance:
        #        good_matches.append(m)

        # print(good_ma)

        # print(keypoints_target)
        # print(keypoints_target[0].octave)


if __name__ == '__main__':
    # src1 = np.float32(cv2.imread('./tests/test1.png', 0))
    # src2 = np.float32(cv2.imread('./tests/test2.png', 0))

    # returns (shift, response) where shift is (x, y)
    # values of x-shift and y-shift and response is higher when
    # there was a single movement (and lower for multiple movements)
    # ret = cv2.phaseCorrelate(src1, src2)
    # print(ret)
    # ret_x = ret[0][0] * np.cos(ret[1])
    # ret_y = ret[0][1] * np.sin(ret[1])
    # print(ret_x)
    # print(ret_y)

    # vc = cv2.VideoCapture('./tests/output.mp4')
    # finder = KeyFrameFinder(0.3, 10, object_detection_threshold=0.4)
    # finder.load_template(
    #    'cursor',
    #    cv2.imread(config.CURSOR_DATA_SAMPLES + '2.png', 0)
    # )
    # kframe, found = finder.select_keyframe2(None, vc)
    # if found:
    #    cv2.imshow('Keyframe', kframe)
    #    cv2.waitKey()
    #    cv2.destroyAllWindows()
    # else:
    #    print('No keyframe found')

    src1 = cv2.imread('./tests/browser2.png')
    src2 = cv2.imread('./data/address_bar/2_r.png', 0)
    kff = KeyFrameFinder(skip_frames=2, object_detection_threshold=0.35)
    print(kff.find_object(src1, src2))
    # src3 = ImagePreprocessing.exaggerate(src1)
    # cv2.imshow('Keyframe', src3)
    # cv2.waitKey()
    # cv2.destroyAllWindows()

    # print(KeyFrameFinder(object_detection_threshold=0.4).find_object(src1, src2))
    # KeyFrameFinder().extended_find_object(src1, src2)

    print('FA')
