import copy
import csv
import datetime
import os
from multiprocessing.queues import Queue

import cv2
from fuzzywuzzy import fuzz
from numpy import ndarray
from pytesseract import pytesseract


class KeyframeMultiprocessingHelper:

    def __init__(self, url_search_keys={}, text_search_keys={}, key_phrases=[], recognition_settings={}):

        self.url_contains_result = copy.deepcopy(url_search_keys)
        self.text_contains_result = copy.deepcopy(text_search_keys)
        self.search_phrases = copy.deepcopy(key_phrases)

        # image preprocessing
        self.use_gray_colors = False
        self.invert_colors = False
        self.use_morphology = False
        self.use_threshold_with_gausian_blur = False
        self.use_adaptiveThreshold = False
        self.increase_image_contrast = False

        self.min_word_confidence = 0
        self.max_y_position_for_URL = 80
        self.comparing_similarity_for_phrases = 80
        self.found_lines = set()
        self.min_word_confidence = 0

        self.save_recognition_data_to_csv = False
        self.save_image_with_recognized_text = False

        self.__load_special_recognition_settings(recognition_settings)

    def __load_special_recognition_settings(self, recognition_settings: dict) -> None:
        if "use_gray_colors" in recognition_settings:
            self.use_gray_colors = recognition_settings["use_gray_colors"]

        if "invert_colors" in recognition_settings:
            self.invert_colors = recognition_settings["invert_colors"]

        if "use_morphology" in recognition_settings:
            self.use_morphology = recognition_settings["use_morphology"]

        if "use_threshold_with_gausian_blur" in recognition_settings:
            self.use_threshold_with_gausian_blur = recognition_settings["use_threshold_with_gausian_blur"]

        if "use_adaptiveThreshold" in recognition_settings:
            self.use_adaptiveThreshold = recognition_settings["use_adaptiveThreshold"]

        if "comparing_similarity_for_phrases" in recognition_settings:
            self.comparing_similarity_for_phrases = recognition_settings["comparing_similarity_for_phrases"]

        if "increase_image_contrast" in recognition_settings:
            self.increase_image_contrast = recognition_settings["increase_image_contrast"]

    def __call__(self, frame: ndarray, result_queue: Queue,  *args, **kwargs):
        self.frame = frame

        image = self.__image_preprocessing()

        recognition_data = pytesseract.image_to_data(image, config=' SET OMP_THREAD_LIMIT=1 ', output_type='dict',)
        # you can try --psm 11 and --psm 6
        # recognition_data = pytesseract.image_to_data(image, output_type='dict')
        # recognition_data2 = pytesseract.image_to_data(image, config='--psm 11', output_type='dict')
        # recognition_data3 = pytesseract.image_to_data(255 - image, output_type='dict')

        if self.save_recognition_data_to_csv:
            self.__save_recognition_csv(recognition_data)

        if self.save_image_with_recognized_text:
            self.__save_recognized_image(frame, recognition_data)
        # cv2.imshow("image", image)
        # cv2.waitKey()

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

    def __save_recognition_csv(self, recognition_data):
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

    def __save_recognized_image(self, src_image, recognition_data):
        image = copy.deepcopy(src_image)
        for i in range(0, len(recognition_data["text"])):
            # extract the bounding box coordinates of the text region from
            x = recognition_data["left"][i]
            y = recognition_data["top"][i]
            w = recognition_data["width"][i]
            h = recognition_data["height"][i]
            # extract the OCR text itself along with the confidence of the
            # text localization
            text = recognition_data["text"][i]
            conf = int(recognition_data["conf"][i])
            if conf < self.min_word_confidence:
                continue

            text = "".join([c if ord(c) < 128 else "" for c in text]).strip()
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 1)
            cv2.putText(image, text, (x, max(10, y - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                        0.3, (0, 0, 255), 1)

        time_suffix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join("recognized_frame_" + time_suffix + ".jpg")

        cv2.imwrite(report_filename, image)
