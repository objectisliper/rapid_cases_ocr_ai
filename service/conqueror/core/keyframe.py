"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Vyacheslav Morozov, 2020
vyacheslav@behealthy.ai
"""
import base64
import csv
import io
import json
import subprocess
import threading
import shlex
from functools import partial

import cv2
import numpy
import pytesseract
from fuzzywuzzy import fuzz


class KeyFrameFinder:

    def __init__(self, motion_threshold=0.5, skip_frames=100,
                 object_detection_threshold=0.5, search_phrases: [str] = [], url_contains: [str] = [],
                 text_contains: [str] = [], recognition_settings={}, byte_video: bytes = b''):
        self.found_lines = []
        self.url_contains_result = {}
        self.text_contains_result = {}
        self.byte_video = byte_video

        # image preprocessing
        self.use_gray_colors = False
        self.invert_colors = False
        self.use_morphology = False
        self.use_threshold_with_gausian_blur = False
        self.use_adaptiveThreshold = False

        self.comparing_similarity_for_phrases = 80
        self.min_word_confidence = 0
        self.threshold = motion_threshold
        self.skip_frames = 50  # skip_frames
        self.max_y_position_for_URL = 100
        self.object_detection_threshold = object_detection_threshold

        self.search_phrases = search_phrases

        for key in url_contains:
            self.url_contains_result[key] = False

        for key in text_contains:
            self.text_contains_result[key] = False

        self.templates = {}

        self.__load_recognition_settings(recognition_settings)

    def process_keyframes(self) -> ([str], dict, dict):
        if not self.byte_video:
            return self.found_lines, self.url_contains_result, self.text_contains_result

        frame_iterator = self.__get_frame_iterator()

        while True:
            # todo: research how we can use CV_CAP_PROP_POS_MSEC or CV_CAP_PROP_POS_FRAMES
            # captured_video.set()
            # CV_CAP_PROP_FPS
            # zzzz = video_handler.get(cv2.CAP_PROP_FRAME_COUNT)
            # zzzz = video_handler.get(cv2.cv2.CAP_PROP_FPS)

            frame = next(frame_iterator)
            print('keyframe step')
            if frame is None:
                break

            image = self.__image_preprocessing(frame)

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

        return self.found_lines, self.url_contains_result, self.text_contains_result

    def __get_frame_iterator(self):
        def writer():
            for chunk in iter(partial(stream.read, 1024), b''):
                process.stdin.write(chunk)
            try:
                process.stdin.close()
            except (BrokenPipeError):
                pass  # For unknown reason there is a Broken Pipe Error when executing FFprobe.

        # Get resolution of video frames using FFprobe
        # (in case resolution is know, skip this part):
        ################################################################################
        # Open In-memory binary streams
        stream = io.BytesIO(self.byte_video)

        process = subprocess.Popen(
            shlex.split('ffprobe -v error -i pipe: -select_streams v -print_format json -show_streams'),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=10 ** 8)

        pthread = threading.Thread(target=writer)
        pthread.start()

        pthread.join()

        in_bytes = process.stdout.read()

        process.wait()

        video_metadata = json.loads(in_bytes)

        width = (video_metadata['streams'][0])['width']
        height = (video_metadata['streams'][0])['height']
        ################################################################################

        # Decoding the video using FFmpeg:
        ################################################################################
        stream.seek(0)

        # FFmpeg input PIPE: WebM encoded data as stream of bytes.
        # FFmpeg output PIPE: decoded video frames in BGR format.
        process = subprocess.Popen(shlex.split('ffmpeg -i pipe: -f rawvideo -pix_fmt bgr24 -an -sn -vf '
                                               f'"select=not(mod(n\,{self.skip_frames}))" -vsync vfr -q:v 2 pipe:'),
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, bufsize=10 ** 8)

        thread = threading.Thread(target=writer)
        thread.start()

        # Read decoded video (frame by frame), and display each frame (using cv2.imshow)
        while True:
            # Read raw video frame from stdout as bytes array.
            in_bytes = process.stdout.read(width * height * 3)

            if not in_bytes:
                stream.close()
                thread.join()
                process.wait(1)
                yield None # Break loop if no more bytes.

            # Transform the byte read into a NumPy array
            in_frame = (numpy.frombuffer(in_bytes, numpy.uint8).reshape([height, width, 3]))

            # return the frame
            yield in_frame

            # for i in range(70):
            #     process.stdout.read(width * height * 3)

    def __image_preprocessing(self, frame):
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

    def __load_recognition_settings(self, recognition_settings):
        settings = recognition_settings.keys()
        if "skip_frames" in settings: self.skip_frames = recognition_settings["skip_frames"]

        if "use_gray_colors" in settings: self.use_gray_colors = recognition_settings["use_gray_colors"]

        if "invert_colors" in settings: self.invert_colors = recognition_settings["invert_colors"]

        if "use_morphology" in settings: self.use_morphology = recognition_settings["use_morphology"]

        if "use_threshold_with_gausian_blur" in settings: self.use_threshold_with_gausian_blur = recognition_settings[
            "use_threshold_with_gausian_blur"]

        if "use_adaptiveThreshold" in settings: self.use_adaptiveThreshold = recognition_settings[
            "use_adaptiveThreshold"]

        if "comparing_similarity_for_phrases" in settings: self.comparing_similarity_for_phrases = recognition_settings[
            "comparing_similarity_for_phrases"]

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

    def __save_if_keyphrase(self, text):
        for phrase in self.search_phrases:
            if text not in self.found_lines \
                    and len(text) + 5 >= len(phrase) \
                    and (
                    fuzz.partial_ratio(phrase, text) >= self.comparing_similarity_for_phrases
                    or
                    phrase.lower() in text.lower()
            ):
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

        for word_index, block_index in enumerate(recognition_data['block_num']):
            if int(recognition_data['conf'][word_index]) > self.min_word_confidence:
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
