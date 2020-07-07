"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Web service endpoint definitions

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import cv2
from flask import request
from flask_restful import Resource
from multiprocessing import Process

from conqueror.app import app, api
from conqueror.core import ImagePreprocessing, KeyFrameFinder, TextPostprocessor
from conqueror.io import VideoFile, Converter
from conqueror.rule_processor import QueryParser, RuleProcessor
from conqueror.delayed_processing import delayed_process


class HealthcheckEndpoint(Resource):
    def get(self):
        return {'result': 1}

class ProcessEndpoint(Resource):
    """
    Main endpoint for processing video data
    and returning the text required
    """
    def post(self):
        # check ruleset
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

        vf = VideoFile(request.data)
        conv = Converter(app.config['VIDEO_TEMP_DIR'], max_hw=0)
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
            cv2.imread(app.config['CURSOR_DATA_SAMPLES'] + '2.png', 0)
        )
        kframe, found, addr, xcpt, rtext = finder.select_keyframe2(None, vc)
        if found:
            #v_ret = VideoFile().from_image(kframe)
            return {
                'id': qp.get_request_id(),
                'text_data': tpp.process(rtext),
                'matches': xcpt
            }
            #return {'result': v_ret.save()}
        else:
            xc, _ = tp.has_match('')
            return {
                'id': qp.get_request_id(),
                'text_data': '',
                'matches': xc
            }


api.add_resource(
    HealthcheckEndpoint,
    '/healthcheck',
    methods=['GET', ]
)
api.add_resource(
    ProcessEndpoint,
    '/process',
    methods=['POST', ]
)
