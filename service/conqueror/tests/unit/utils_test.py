import time
from unittest import TestCase

from service.conqueror.utils import get_amazon_server_signature


class UtilsTestCase(TestCase):

    def setUp(self) -> None:
        pass

    def test_get_amazon_server_signature(self):
        timestamp = 1597764590377
        job_id = 'LlpjHueW0XYYH87vkN7-TafctB39TU_b'
        result = get_amazon_server_signature(job_id, timestamp)
        self.assertEqual(result, 'eZy1SN65HywbNuBaPJHNuzVqsTA%3D')

