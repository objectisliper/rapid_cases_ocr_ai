"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import pytesseract
from fuzzywuzzy import fuzz


class KeyFrameFinder:
    found_lines = []
    url_contains_result = {}
    text_contains_result = {}
    needed_ratio = 85

    def __init__(self, motion_threshold=0.5, skip_frames=100,
                 object_detection_threshold=0.5, search_phrases: [str] = [], url_contains: [str] = [],
                 text_contains: [str] = []):

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

            text_by_lines = self.__combine_by_line_number(pytesseract.image_to_data(frame[..., 0], output_type='dict'))

            self.__check_is_special_contains(''.join(text_by_lines))

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

    def __combine_by_line_number(self, image_data: dict, lines_in_string: int = 1):
        result_list = []

        for index, value in enumerate(image_data['line_num']):
            line_next_word = image_data['text'][index]

            if value > 0 and lines_in_string > 1:
                value = int(((value + 1) - (value + 1) % lines_in_string) / lines_in_string)
                if value > 0:
                    value -= 1

            if len(result_list) >= value + 1:
                result_list[value] = result_list[value] + ' ' + line_next_word
            else:
                result_list.append(line_next_word)

        return result_list
