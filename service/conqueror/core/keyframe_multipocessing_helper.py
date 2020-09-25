import copy
from multiprocessing.queues import Queue

import cv2
from fuzzywuzzy import fuzz
from numpy import ndarray
from pytesseract import pytesseract


class KeyframeMultiprocessingHelper:

    def __init__(self, **kwargs):

        self.url_contains_result = copy.deepcopy(kwargs.get('url_search_keys', {}))
        self.text_contains_result = copy.deepcopy(kwargs.get('text_search_keys', {}))
        self.search_phrases = copy.deepcopy(kwargs.get('key_phrases', []))

        self.max_y_position_for_URL = 80
        self.comparing_similarity_for_phrases = 80
        self.found_lines = set()
        self.min_word_confidence = 0

        # image preprocessing
        self.use_gray_colors = False
        self.invert_colors = False
        self.use_morphology = False
        self.use_threshold_with_gausian_blur = False
        self.use_adaptiveThreshold = False
        self.increase_image_contrast = False

        self.__load_recognition_settings(kwargs.get('recognition_settings', {}))

    def __call__(self, frame: ndarray, result_queue: Queue, process_id,  *args, **kwargs):
        self.frame = frame

        image = self.__image_preprocessing()

        recognition_data = pytesseract.image_to_data(image, config=' SET OMP_THREAD_LIMIT=1 ', output_type='dict',)

        self.__check_search_rules(recognition_data)

        result_queue.put((self.url_contains_result, self.text_contains_result, self.found_lines))

    def __check_search_rules(self, recognition_data):
        url_blocks, page_blocks = self.__get_blocks(recognition_data)
        for line_text in page_blocks:
            if line_text == '':
                continue

            if self.max_y_position_for_URL < 1:
                self.__check_url_contains(line_text)
            self.__check_text_contains(line_text)
            self.__save_if_keyphrase(line_text)

        if self.max_y_position_for_URL > 0:

            for line_text in url_blocks:
                if line_text == '':
                    continue

                self.__check_url_contains(line_text)

    def __get_blocks(self, recognition_data: dict):
        url_blocks = {}
        page_blocks = {}

        for word_index, block_index in enumerate(recognition_data['block_num']):
            if int(recognition_data['conf'][word_index]) > self.min_word_confidence:
                if recognition_data['top'][word_index] > self.max_y_position_for_URL:
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

    def __check_text_contains(self, whole_page_text):
        for key in self.text_contains_result.keys():
            if not self.text_contains_result[key] \
                    and len(whole_page_text) + 5 >= len(key) \
                    and (
                    key in whole_page_text
                    or
                    fuzz.partial_ratio(key, whole_page_text) >= self.comparing_similarity_for_phrases
            ):
                self.text_contains_result[key] = True

    def __check_url_contains(self, whole_page_text):
        for key in self.url_contains_result.keys():
            if not self.url_contains_result[key] \
                    and len(whole_page_text) + 5 >= len(key) \
                    and (
                    key.lower() in whole_page_text.lower()
                    or
                    fuzz.partial_ratio(key, whole_page_text) >= self.comparing_similarity_for_phrases
            ):
                self.url_contains_result[key] = True

    def __save_if_keyphrase(self, text):
        for phrase in self.search_phrases:
            if len(text) + 5 >= len(phrase) \
                    and (
                    fuzz.partial_ratio(phrase, text) >= self.comparing_similarity_for_phrases
                    or
                    phrase.lower() in text.lower()
            ):
                self.found_lines.add(text)

    def __image_preprocessing(self) -> ndarray:
        image = self.frame[..., 0]

        if self.use_adaptiveThreshold:
            image = cv2.adaptiveThreshold(image, 220, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 2)

        if self.use_gray_colors:
            image = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)

        if self.use_threshold_with_gausian_blur:
            blur = cv2.GaussianBlur(image, (3, 3), 0)
            image = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        if self.use_morphology:
            # Morph open to remove noise
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel, iterations=1)

        if self.increase_image_contrast:
            contrast = 64
            f = 131 * (contrast + 127) / (127 * (131 - contrast))
            alpha_c = f
            gamma_c = 127 * (1 - f)
            image = cv2.addWeighted(image, alpha_c, image, 0, gamma_c)

        if self.invert_colors:
            image = 255 - image

        return image

    def __load_recognition_settings(self, recognition_settings: dict) -> None:
        settings = recognition_settings.keys()
        if "skip_frames" in settings:
            self.skip_frames = recognition_settings["skip_frames"]

        if "use_gray_colors" in settings:
            self.use_gray_colors = recognition_settings["use_gray_colors"]

        if "invert_colors" in settings:
            self.invert_colors = recognition_settings["invert_colors"]

        if "use_morphology" in settings:
            self.use_morphology = recognition_settings["use_morphology"]

        if "use_threshold_with_gausian_blur" in settings:
            self.use_threshold_with_gausian_blur = recognition_settings["use_threshold_with_gausian_blur"]

        if "use_adaptiveThreshold" in settings:
            self.use_adaptiveThreshold = recognition_settings["use_adaptiveThreshold"]

        if "comparing_similarity_for_phrases" in settings:
            self.comparing_similarity_for_phrases = recognition_settings["comparing_similarity_for_phrases"]

        if "increase_image_contrast" in settings:
            self.increase_image_contrast = recognition_settings["increase_image_contrast"]
