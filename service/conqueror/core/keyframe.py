"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import cv2
import imutils
import numpy as np
import pytesseract

from .base import StatefulObject
from .text_detection import TextExtractor, TextPostprocessor


class KeyFrameFinder(StatefulObject):
    """
    Class that contains methods to find a keyframe
    (steady frame where selection is over and no
    or almost no motion is present)
    """
    class Meta:
        state_file = './trained/keyframefinder.obj'

    def __init__(self, motion_threshold=0.5, skip_frames=100,
    object_detection_threshold=0.5, text_processor=None):
        self.threshold = motion_threshold
        self.skip_frames = 200 #skip_frames
        self.object_detection_threshold = object_detection_threshold

        self.templates = {}
        self.te = TextExtractor(processor=text_processor)

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

            #frame = ImagePreprocessing.exaggerate(frame)

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
                rtext = pytesseract.image_to_string(frame[..., 0])
                mm, has_any = self.te.has_exception(rtext)
                if has_any:
                    #excpt = self.te.extract_exception(rtext)
                    addr = self.te.extract_address(rtext)
                    return frame, True, addr, mm, rtext

            for i in range(self.skip_frames):
                video_handler.read()

        return None, False, None, None, ''

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
            #template = cv2.Canny(template_image, 100, 200)
        else:
            gray = ImagePreprocessing.exaggerate(target_image)
            template = template_image

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

            if delta > self.object_detection_threshold:
                # object found
                object_found = True

                if delta > current_max:
                    current_max = delta
                    object_loc = max_loc

        if object_found:
            return object_loc

        return None
