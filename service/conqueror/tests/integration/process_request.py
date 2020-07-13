import base64
import json
import pathlib
import zlib
from unittest import TestCase

from service.conqueror.managers import process_request


class RequestMock:
    def __init__(self, data):
        self.data = data


class ProcessRequestIntegrationTest(TestCase):

    def setUp(self) -> None:
        pass

    def test_process_request(self):
        config_path = (pathlib.Path(__file__).parent.parent / 'integration_tests_video' / '7bbfc76b.mp4').as_posix()
        request = {}
        with open(config_path, 'rb') as video:
            request['video'] = base64.b64encode(video.read()).decode('utf-8')
        raw_sign = zlib.crc32(request['video'].encode('utf-8')) & 0xffffffff
        request['checksum'] = '{:08x}'.format(raw_sign)
        json_encoded_request = json.dumps(request)
        result = process_request(RequestMock(json_encoded_request))
        self.assertIn('System DmlException: Insert failed. First exception on row 0: first error: REQUIRED '
                      'FIELD_MISSING, Required fields are missing: [LastName]: [LastName]', result['text_data'])
