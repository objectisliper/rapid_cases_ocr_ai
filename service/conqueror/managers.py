"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Delayed processing routines

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
from multiprocessing.context import Process

import cv2
import logging
import requests

from .io import VideoFile, Converter
from .core import KeyFrameFinder, TextPostprocessor
from .rule_processor import QueryParser, RuleProcessor
from .settings.local import DELAYED_RESPONSE_ENDPOINT, VIDEO_TEMP_DIR, CURSOR_DATA_SAMPLES

logger = logging.getLogger('async_response')


def delayed_response(resp_data):
    ret = requests.post(
        DELAYED_RESPONSE_ENDPOINT,
        json=resp_data
    ).json()

    logger.warning(resp_data)
    if 'response_code' in ret:
        logger.warning('Data sent to endpoint\n%s' % str(ret))
    else:
        logger.error('Error sending data to endpoint\n%s' % str(ret))

    # TODO: add response processing


def delayed_process(request_data, qp, tp, tpp):
    """
    Main method for delayed request processing
    """
    result = process_video(qp, request_data, tp, tpp)

    delayed_response(result)


def process_request(request):
    qp = QueryParser(request.data)
    tp = RuleProcessor(qp.parse())
    tpp = TextPostprocessor()

    if qp.get_async_flag():
        p = Process(target=delayed_process, args=(request.data, qp, tp, tpp))
        p.start()
        return {
            'success': 1,
            'status': 'processing'
        }

    return process_video(request.data, qp, tp, tpp)


def process_video(qp, request_data, tp, tpp):
    vf = VideoFile(request_data)
    conv = Converter(VIDEO_TEMP_DIR, max_hw=0)
    vf = conv.process(vf)
    vc = cv2.VideoCapture(vf.stored_file)
    finder = KeyFrameFinder(
        0.3,
        10,
        object_detection_threshold=0.4,
        text_processor=tp
    )
    finder.load_template(
        'cursor',
        cv2.imread(CURSOR_DATA_SAMPLES + '2.png', 0)
    )
    kframe, found, addr, xcpt, rtext = finder.select_keyframe2(None, vc)
    if found:
        # v_ret = VideoFile().from_image(kframe)
        result = {
            'case_id': qp.get_request_id(),
            'text_data': tpp.process(rtext),
            'matches': xcpt
        }
    else:
        xc, _ = tp.has_match('')
        result = {
            'case_id': qp.get_request_id(),
            'text_data': '',
            'matches': xc
        }
    return result
