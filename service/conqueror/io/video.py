"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Input/output and file validation routines

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import cv2
import json
import zlib
import base64


class VideoFile(object):
    # container class for video files
    def __init__(self, json_data=None):
        self.video_data = None
        self.signature = None
        self.format = 'mp4'
        self.stored_file = None

        if json_data:
            self.load(json_data)

    def from_image(self, image_data):
        ret, png_data = cv2.imencode('.png', image_data)
        self.video_data = png_data.tobytes()
        self.format = 'png'
        self.recalculate_signature()

        return self

    @staticmethod
    def _sign(data):
        raw_sign = zlib.crc32(data.encode('utf-8')) & 0xffffffff
        return '{:08x}'.format(raw_sign)

    def load(self, raw_data):
        raw = json.loads(raw_data)

        if 'VideoBody' in raw:
            self.video_data = base64.b64decode(raw['VideoBody'])
        else:
            raise Exception('Invalid data supplied')

    def save(self):
        video_b64 = base64.b64encode(self.video_data).decode('utf-8')
        signature = self.signature if self.signature else \
        VideoFile._sign(video_b64)

        return {
            'video': video_b64,
            'checksum': signature,
            'format': self.format
        }

    def recalculate_signature(self):
        video_b64 = base64.b64encode(self.video_data).decode('utf-8')
        self.signature = VideoFile._sign(video_b64)
        return self.signature
