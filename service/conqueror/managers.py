"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Delayed processing routines

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import base64
import json
import os
import signal

from .core.keyframe import KeyFrameFinder
from .utils import timeout_handler


def process_request(data: str, recognition_settings: dict = None):
    if recognition_settings is None:
        recognition_settings = {}
    return process_video(data, recognition_settings)


def process_video(request_data: str, recognition_settings):
    data = json.loads(request_data)

    # video_file.stored_file = save_video_to_temporary_directory(video_file)
    # # TODO Need preprocessing, maybe creating a pictures and preprocess image
    # captured_video = cv2.VideoCapture(video_file.stored_file)
    keyframe_finder = KeyFrameFinder(0.3, object_detection_threshold=0.4,
                                     search_phrases=data['SearchPhraseIdentifiers'], url_contains=data['URLContains'],
                                     text_contains=data['TextContains'], recognition_settings=recognition_settings,
                                     byte_video=base64.b64decode(data['VideoBody']))

    # Set timeout for processing
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(os.environ.get('RECOGNITION_TIMEOUT_SECONDS', 1800)))

    found_lines, url_contains_results, text_contains_result = keyframe_finder.process_keyframes()

    signal.alarm(0)

    return {
        'SearchPhrasesFound': found_lines,
        'URLContainsResults': url_contains_results,
        'TextContainsResults': text_contains_result
    }
