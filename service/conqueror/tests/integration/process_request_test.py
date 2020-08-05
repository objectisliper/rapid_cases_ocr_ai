import base64
import json
import pathlib
import zlib
from unittest import TestCase

from service.conqueror.managers import process_request


class ProcessRequestIntegrationTest(TestCase):

    def setUp(self) -> None:
        pass

    def test_process_request(self):
        config_path = (pathlib.Path(__file__).parent.parent / 'integration_tests_video' / '2730cfc6.webm').as_posix()
        request = {}
        with open(config_path, 'rb') as video:
            request['video'] = base64.b64encode(video.read()).decode('utf-8')
        raw_sign = zlib.crc32(request['video'].encode('utf-8')) & 0xffffffff
        request['checksum'] = '{:08x}'.format(raw_sign)
        request['format'] = 'webm'
        json_encoded_request = json.dumps(request)
        result = process_request(json_encoded_request)

        self.assertIn('&        Home @x Hor x + - a x C  @ onlinestore-developer-editionnat74force.com/mystore/s/ x '
                      '© @ Error Contact Form System DmlException: Insert failed. First exception on row O; '
                      'first erro Tag No eae eh ea [LastName FirstName  Last Name  fered  '
                      'Npsnoxenito onlinestore-developer-edition.na174force.com npegocrasnen AOCTyn K BaUleMy skpaHy  '
                      '1545 Aa ans gE 20.03.2020 Oo', result['text_data'])
