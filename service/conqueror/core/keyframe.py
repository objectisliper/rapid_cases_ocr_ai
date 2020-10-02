"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Vyacheslav Morozov, 2020
vyacheslav@behealthy.ai
"""
import base64
import copy
import csv
import io
import json
import multiprocessing
import subprocess
import threading
import shlex
from copy import deepcopy
import datetime, os
from functools import partial
from multiprocessing import Queue

import cv2
import numpy

from service.conqueror.core.keyframe_multipocessing_helper import KeyframeMultiprocessingHelper


class KeyFrameFinder:

    @property
    def __video_filter_settings(self):
        video_filter_setting = '-vf '
        if self.fps_instead_skip_frames:
            video_filter_setting += f'fps=fps={self.frame_per_second}'
        else:
            video_filter_setting += f'framestep={self.skip_frames}'
        return video_filter_setting

    def __init__(self, motion_threshold=0.5,
                 object_detection_threshold=0.5, search_phrases: [str] = [], url_contains: [str] = [],
                 text_contains: [str] = [], recognition_settings={}, byte_video: bytes = b''):

        self.recognition_settings = recognition_settings
        self.__load_iteration_settings()

        self.found_lines = []
        self.url_contains_result = {}
        self.text_contains_result = {}
        self.byte_video = byte_video

        self.save_recognition_data_to_csv = False
        self.save_image_with_recognized_text = True

        self.comparing_similarity_for_phrases = 80
        self.min_word_confidence = 0
        self.threshold = motion_threshold
        self.frame_per_second = 2

        self.max_y_position_for_URL = 80
        self.object_detection_threshold = object_detection_threshold
        self.stop_on_first_keyframe_found = False

        self.search_phrases = search_phrases

        for key in url_contains:
            self.url_contains_result[key] = False

        for key in text_contains:
            self.text_contains_result[key] = False

        self.templates = {}

    def process_keyframes(self) -> ([str], dict, dict):
        if not self.byte_video:
            return self.found_lines, self.url_contains_result, self.text_contains_result

        frame_iterator = self.__get_frame_iterator()

        final_url_result = copy.deepcopy(self.url_contains_result)

        final_text_result = copy.deepcopy(self.text_contains_result)

        final_key_phrase_result = set()

        cpu_count = multiprocessing.cpu_count() if self.multiprocessing else 1

        print(f'Now i will use {cpu_count} core')

        result_queue = Queue()

        if multiprocessing:

            os.environ['OMP_THREAD_LIMIT'] = '1'

        process_frame = True

        while process_frame:
            # Todo Для этого есть переменные окружения, свойства класса использовать для такого - плохо.

            # if self.stop_on_first_keyframe_found:
            #     if len(self.found_lines) > 0:
            #         break

            process_list = []

            for i in range(cpu_count):
                frame = next(frame_iterator)
                if frame is None:
                    process_frame = False
                    print('final keyframe')
                    break

                frame_processor = KeyframeMultiprocessingHelper(url_search_keys=self.url_contains_result,
                                                                text_search_keys=self.text_contains_result,
                                                                key_phrases=self.search_phrases,
                                                                recognition_settings=self.recognition_settings)

                process = multiprocessing.Process(target=frame_processor, args=(frame, result_queue))
                process_list.append(process)
                process.start()

            if len(process_list) < 1:
                break

            for process in process_list:
                (url_result, text_result, key_phrases_result) = result_queue.get()

                final_url_result = {key: final_url_result[key] or item for key, item in url_result.items()}

                final_text_result = {key: final_text_result[key] or item for key, item in text_result.items()}

                final_key_phrase_result = final_key_phrase_result.union(key_phrases_result)

            for process in process_list:
                process.join()

        result_queue.close()

        return list(final_key_phrase_result), final_url_result, final_text_result

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

        process = subprocess.Popen(shlex.split('ffmpeg -i pipe: -f rawvideo -pix_fmt bgr24 -an -sn '
                                               f'{self.__video_filter_settings} '
                                               f'-vsync vfr -q:v 2 pipe:'),
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
                yield None  # Break loop if no more bytes.

            # Transform the byte read into a NumPy array
            in_frame = (numpy.frombuffer(in_bytes, numpy.uint8).reshape([height, width, 3]))

            # return the frame
            yield in_frame

            # for i in range(70):
            #     process.stdout.read(width * height * 3)

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

    def __save_recognized_image(self, src_image, recognition_data):
        image = deepcopy(src_image)
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

    def __load_iteration_settings(self):
        self.skip_frames = self.recognition_settings.get('skip_frames', 50)

        self.fps_instead_skip_frames = self.recognition_settings.get('fps_instead_skip_frames', True)

        self.multiprocessing = self.recognition_settings.get('multiprocessing', True)
