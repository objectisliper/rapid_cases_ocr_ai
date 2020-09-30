import json
import os
import sys
import time
from unittest import TestCase
from unittest.mock import patch, NonCallableMock

from service.conqueror.managers import process_request, process_video, KeyFrameFinder
from service.conqueror.utils import RecognitionTimeoutException


class ProcessKeyframeTimeout:
    def __init__(self, timeout_seconds: int, process_keyframe_result_data: tuple):
        self.timeout_seconds = timeout_seconds
        self.process_keyframe_result_data = process_keyframe_result_data

    def __call__(self, *args, **kwargs):
        time_to_sleep = self.timeout_seconds
        result_data = self.process_keyframe_result_data

        def closure_function(*args, **kwargs):
            time.sleep(time_to_sleep + 1)

            return result_data

        return closure_function


class ProcessRequestTestCase(TestCase):

    def setUp(self) -> None:
        pass

    @patch('service.conqueror.managers.process_video')
    def test_process_request_with_recognition_settings(self, process_video_function: NonCallableMock):
        test_data = json.dumps({'test_data_key': 'test_data_value'})
        test_settings = {'test_key': 'test_value'}
        process_request(test_data, test_settings)

        process_video_function.assert_called_once_with(test_data, test_settings)

    @patch('service.conqueror.managers.process_video')
    def test_process_request_without_recognition_settings(self, process_video_function: NonCallableMock):
        test_data = json.dumps({'test_data_key': 'test_data_value'})
        process_request(test_data)

        process_video_function.assert_called_once_with(test_data, {})


class ProcessVideoTestCase(TestCase):
    process_keyframe_result_data = (['test'], {'test': 'test'}, {'test': 'test'})
    process_video_expected_result_data = {}
    timeout_seconds = 4
    process_keyframe_timeout_function = ProcessKeyframeTimeout(timeout_seconds, process_keyframe_result_data)

    def setUp(self) -> None:
        self.process_video_expected_result_data = {
            'SearchPhrasesFound': self.process_keyframe_result_data[0],
            'URLContainsResults': self.process_keyframe_result_data[1],
            'TextContainsResults': self.process_keyframe_result_data[2]
        }

    @patch.object(KeyFrameFinder, 'process_keyframes',
                  return_value=process_keyframe_result_data)
    def test_process_video_without_timeout(self, process_keyframes: NonCallableMock):
        test_data = json.dumps({'SearchPhraseIdentifiers': 'test_data_value', 'URLContains': 'test_data',
                                'TextContains': 'test_data', 'VideoBody': 'test_data'})
        test_settings = {'test_key': 'test_value'}

        process_video_real_result = process_video(test_data, test_settings)

        process_keyframes.assert_called_once()
        self.assertDictEqual(process_video_real_result, self.process_video_expected_result_data)

    @patch.object(KeyFrameFinder, 'process_keyframes',
                  new_callable=process_keyframe_timeout_function)
    def test_process_video_with_timeout(self, process_keyframes: NonCallableMock):
        if sys.platform.startswith('win32'):
            self.skipTest('Because windows is not cool enough')
        test_data = json.dumps({'SearchPhraseIdentifiers': 'test_data_value', 'URLContains': 'test_data',
                                'TextContains': 'test_data', 'VideoBody': 'test_data'})
        test_settings = {'test_key': 'test_value'}
        os.environ['RECOGNITION_TIMEOUT_SECONDS'] = str(self.timeout_seconds)

        with self.assertRaises(RecognitionTimeoutException):
            process_video(test_data, test_settings)
