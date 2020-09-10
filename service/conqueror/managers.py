"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Delayed processing routines

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import json
from multiprocessing.context import Process

import cv2
import logging

from .core.keyframe import KeyFrameFinder
from .io import VideoFile
from .utils import save_video_to_temporary_directory

logger = logging.getLogger('async_response')

default_rule = """
    {
        "rules": [{
    	"id": 151212,
        "steps": [
    	    {
                "order": 0,
                "URLcondition": "!contains",
                "exact": 0,
                "URLtext": "someth",
                "ConditionsLogic": "and",
                "PageContentsCondition": "contains",
                "PageText": "exception"
    	    }
          ]
    }]
    }
    """


def process_request(data, recognition_settings={}):
    return process_video(data, recognition_settings)


def process_video(request_data: str, recognition_settings={}):
    data = json.loads(request_data)

    video_file = VideoFile(request_data)
    video_file.stored_file = save_video_to_temporary_directory(video_file)
    # TODO Need preprocessing, maybe creating a pictures and preprocess image
    captured_video = cv2.VideoCapture(video_file.stored_file)
    keyframe_finder = KeyFrameFinder(0.3, 10, object_detection_threshold=0.4,
                                     search_phrases=data['SearchPhraseIdentifiers'], url_contains=data['URLContains'],
                                     text_contains=data['TextContains'], recognition_settings=recognition_settings)

    found_lines, url_contains_results, text_contains_result = keyframe_finder.process_keyframes(captured_video)

    return {
        'SearchPhrasesFound': found_lines,
        'URLContainsResults': url_contains_results,
        'TextContainsResults': text_contains_result
    }
