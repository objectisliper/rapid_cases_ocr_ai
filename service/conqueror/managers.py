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

from service.conqueror.io.video_saver import VideoSaver
from .io import VideoFile, Converter
from .core import KeyFrameFinder, TextPostprocessor
from .rule_processor import QueryParser, RuleProcessor
from .settings.local import DELAYED_RESPONSE_ENDPOINT, VIDEO_TEMP_DIR, CURSOR_DATA_SAMPLES

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


def delayed_process(request_data, qp, tp, tpp, vp):
    """
    Main method for delayed request processing
    """
    result = process_video(qp, request_data, tp, tpp, vp)

    delayed_response(result)


def process_request(data):
    qp = QueryParser(default_rule)
    tp = RuleProcessor(qp.parse())
    tpp = TextPostprocessor()
    # vp = Converter(VIDEO_TEMP_DIR, max_hw=0)
    vp = VideoSaver(VIDEO_TEMP_DIR, max_hw=0)

    if qp.get_async_flag():
        p = Process(target=delayed_process, args=(data, qp, tp, tpp, vp))
        p.start()
        return {
            'success': 1,
            'status': 'processing'
        }

    return process_video(data, qp, tp, tpp, vp)


def process_video(request_data, qp, tp, tpp, vp):
    vf = VideoFile(request_data)
    vf = vp.process(vf)
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
    print(rtext)
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
