"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Vyacheslav Morozov, 2020
vyacheslav@behealthy.ai
"""
import csv

import cv2
import pytesseract
from fuzzywuzzy import fuzz


class KeyFrameFinder:

    def __init__(self, motion_threshold=0.5, skip_frames=100,
                 object_detection_threshold=0.5, search_phrases: [str] = [], url_contains: [str] = [],
                 text_contains: [str] = [], recognition_settings={}):
        self.found_lines = []
        self.url_contains_result = {}
        self.text_contains_result = {}

        # image preprocessing
        self.use_gray_colors = False
        self.invert_colors = False
        self.use_morphology = False
        self.use_threshold_with_gausian_blur = False
        self.use_adaptiveThreshold = False

        self.needed_ratio = 80
        self.threshold = motion_threshold
        self.skip_frames = 30  # skip_frames
        self.max_y_position_for_URL = 100
        self.object_detection_threshold = object_detection_threshold

        self.search_phrases = search_phrases

        for key in url_contains:
            self.url_contains_result[key] = False

        for key in text_contains:
            self.text_contains_result[key] = False

        self.templates = {}

        self.__load_recognition_settings(recognition_settings)

    def __load_recognition_settings(self, recognition_settings):
        settings = recognition_settings.keys()
        if "skip_frames" in settings: self.skip_frames = recognition_settings["skip_frames"]

        if "use_gray_colors" in settings: self.use_gray_colors = recognition_settings["use_gray_colors"]

        if "invert_colors" in settings: self.invert_colors = recognition_settings["invert_colors"]

        if "use_morphology" in settings: self.use_morphology = recognition_settings["use_morphology"]

        if "use_threshold_with_gausian_blur" in settings: self.use_threshold_with_gausian_blur = recognition_settings["use_threshold_with_gausian_blur"]

        if "use_adaptiveThreshold" in settings: self.use_adaptiveThreshold = recognition_settings["use_adaptiveThreshold"]

    def __save_recognition_csv(self, recognition_data):
        import datetime, os
        time_suffix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join("recognize_dict" + time_suffix + ".csv")
        try:
            with open(report_filename, 'w', encoding='utf-8', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(list(recognition_data.keys()))
                for index, text in enumerate(recognition_data['text']):
                    row = [recognition_data['level'][index],
                                     recognition_data['page_num'][index],
                                     recognition_data['block_num'][index],
                                     recognition_data['par_num'][index],
                                     recognition_data['line_num'][index],
                                     recognition_data['word_num'][index],
                                     recognition_data['left'][index],
                                     recognition_data['top'][index],
                                     recognition_data['width'][index],
                                     recognition_data['height'][index],
                                     recognition_data['conf'][index],
                                     text]
                    writer.writerow(row)
        except IOError:
            print("I/O error")

    def process_keyframes(self, video_handler) -> ([str], dict, dict):
        while True:
            # todo: research how we can use CV_CAP_PROP_POS_MSEC or CV_CAP_PROP_POS_FRAMES
            # captured_video.set()
            #CV_CAP_PROP_FPS
            # zzzz = video_handler.get(cv2.CAP_PROP_FRAME_COUNT)
            # zzzz = video_handler.get(cv2.cv2.CAP_PROP_FPS)

            result, frame = video_handler.read()
            print('keyframe step')
            if not result:
                break

            image = self.image_preprocessing(frame)

            # you can try --psm 11 and --psm 6
            whole_page_text = pytesseract.image_to_data(image, output_type='dict')
            # whole_page_text2 = pytesseract.image_to_data(image, config='--psm 6', output_type='dict')
            # self.__save_recognition_csv(whole_page_text)
            url_blocks, page_blocks = self.__get_blocks(whole_page_text)

            # text_by_lines = self.__get_page_text_by_lines(whole_page_text)

            # self.__check_is_special_contains(' '.join(whole_page_text['text']))

            # for line_text in blocks:
            # for line_text in text_by_lines:
            for line_text in page_blocks:
                if line_text == '':
                    continue

                # self.__check_text_contains(whole_page_text)
                self.__check_text_contains(line_text)
                # self.__check_url_contains(whole_page_text)
                self.__save_if_keyphrase(line_text)

            for line_text in url_blocks:
                if line_text == '':
                    continue

                # self.__check_url_contains(whole_page_text)
                self.__check_url_contains(line_text)

            # stop on first keyframe found
            # if len(self.found_lines) > 0:
            #     break
            for i in range(self.skip_frames):
                video_handler.read()

        return self.found_lines, self.url_contains_result, self.text_contains_result

    def image_preprocessing(self, frame):
        image = frame[..., 0]

        if self.use_adaptiveThreshold:
            image = cv2.adaptiveThreshold(image, 220, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 2)

        if self.use_gray_colors:
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self.use_threshold_with_gausian_blur:
            blur = cv2.GaussianBlur(image, (3, 3), 0)
            image = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        if self.use_morphology:
            # Morph open to remove noise
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel, iterations=1)

        if self.invert_colors:
            image = 255 - image

        return image

    def __check_text_contains(self, whole_page_text):
        for key in self.text_contains_result.keys():
            if not self.text_contains_result[key] and len(whole_page_text) + 5 >= len(key) and \
                    (key in whole_page_text or fuzz.partial_ratio(key, whole_page_text) >= self.needed_ratio):
                self.text_contains_result[key] = True

    def __check_url_contains(self, whole_page_text):
        for key in self.url_contains_result.keys():
            if not self.url_contains_result[key] and len(whole_page_text) + 5 >= len(key) and \
                    (key in whole_page_text or fuzz.partial_ratio(key, whole_page_text) >= self.needed_ratio):
                self.url_contains_result[key] = True

    def __save_if_keyphrase(self, text):
        for phrase in self.search_phrases:
            if len(text) + 5 >= len(phrase) and text not in self.found_lines and \
                    fuzz.partial_ratio(phrase, text) >= self.needed_ratio:
                    # phrase.lower() in text.lower():
                self.found_lines.append(text)

    def __get_page_text_by_lines(self, image_data: dict):
        result_list = {}

        for index, value in enumerate(image_data['top']):

            line_next_word = image_data['text'][index]

            if result_list.get(str(value)):
                result_list[str(value)] = result_list.get(str(value)) + ' ' + line_next_word
            else:
                result_list[str(value)] = line_next_word

        result_list = list(set(result_list.values()))

        return result_list

    def __get_blocks(self, recognition_data: dict):
        url_blocks = {}
        page_blocks = {}
        min_confidence = 0

        for word_index, block_index in enumerate(recognition_data['block_num']):
            if int(recognition_data['conf'][word_index]) > min_confidence:
                if recognition_data['top'][word_index] > self.max_y_position_for_URL:
                # if recognition_data['top'][word_index] > -100:
                    if block_index in page_blocks:
                        page_blocks[block_index] = page_blocks[block_index] + ' ' + recognition_data['text'][word_index]
                    else:
                        page_blocks[block_index] = recognition_data['text'][word_index]
                else:
                    if block_index in url_blocks:
                        url_blocks[block_index] = url_blocks[block_index] + ' ' + recognition_data['text'][word_index]
                    else:
                        url_blocks[block_index] = recognition_data['text'][word_index]

        result_url_blocks = [block for block in url_blocks.values() if len(block.strip()) > 0]
        result_page_blocks = [block for block in page_blocks.values() if len(block.strip()) > 0]
        return result_url_blocks, result_page_blocks
