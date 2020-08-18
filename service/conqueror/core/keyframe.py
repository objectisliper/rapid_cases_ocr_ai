"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import cv2
import pytesseract
from fuzzywuzzy import fuzz


class KeyFrameFinder:

    def __init__(self, motion_threshold=0.5, skip_frames=100,
                 object_detection_threshold=0.5, search_phrases: [str] = [], url_contains: [str] = [],
                 text_contains: [str] = []):
        self.found_lines = []
        self.url_contains_result = {}
        self.text_contains_result = {}
        self.needed_ratio = 80
        self.threshold = motion_threshold
        self.skip_frames = 50  # skip_frames
        self.object_detection_threshold = object_detection_threshold

        self.search_phrases = search_phrases

        for key in url_contains:
            self.url_contains_result[key] = False

        for key in text_contains:
            self.text_contains_result[key] = False

        self.templates = {}

    def process_keyframes(self, video_handler) -> ([str], dict, dict):
        while True:
            result, frame = video_handler.read()
            print('keyframe step')
            if not result:
                break

            image = frame[..., 0]
            #
            # image = cv2.adaptiveThreshold(image, 220, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 2)

            # you can try --psm 11 and --psm 6
            whole_page_text = pytesseract.image_to_data(image, output_type='dict')

            text_by_lines = self.__get_page_text_by_lines(whole_page_text)

            self.__check_is_special_contains(' '.join(whole_page_text['text']))

            for line_text in text_by_lines:
                if line_text == '':
                    continue

                self.__save_if_keyphrase(line_text)

            for i in range(self.skip_frames):
                video_handler.read()

        return self.found_lines, self.url_contains_result, self.text_contains_result

    def __check_is_special_contains(self, whole_page_text):
        for key in self.url_contains_result.keys():
            if not self.url_contains_result[key] and len(whole_page_text) >= len(key) and \
                    fuzz.partial_ratio(key, whole_page_text) >= self.needed_ratio:
                self.url_contains_result[key] = True

        for key in self.text_contains_result.keys():
            if not self.text_contains_result[key] and len(whole_page_text) >= len(key) and \
                    fuzz.partial_ratio(key, whole_page_text) >= self.needed_ratio:
                self.text_contains_result[key] = True

    def __save_if_keyphrase(self, text):

        for phrase in self.search_phrases:
            if len(text) >= len(phrase) and text not in self.found_lines and \
                    fuzz.partial_ratio(phrase, text) >= self.needed_ratio:
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
