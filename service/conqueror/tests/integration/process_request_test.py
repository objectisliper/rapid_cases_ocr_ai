import base64
import json
import pathlib
import zlib
from unittest import TestCase

from service.conqueror.managers import process_request

# Таким образом JSON типичного запроса будет выглядеть примерно так
# {
# SearchPhraseIdentifiers:["error", "exception"],
# URLContains:["wpadmin", "wordpress.com"], //тут будет полный массив со ВСЕХ рулов
# TextContains:["MySQL", "MariaDB"], //тут будет полный массив со ВСЕХ рулов
# VideoBody: "sfasfadfa23dflskf;l….sdfasf"
# }
#
#
# Ответ на такой запрос должен быть примерно такой
# {
# SearchPhrasesFound:["Contact validation error: Last name is missing.",
# "Mysql error: username and password are not correct"],
# URLContainsResults:["wpadmin"=true, "wordpress.com"=false], //найдено было каждое слово в урле или нет
# TextContainsResults:["MySQL"=true, "MariaDB"=false], // найдено было каждое слово в урле или нет
# }


class ProcessRequestIntegrationTest(TestCase):

    def setUp(self) -> None:
        pass

    def test_process_request(self):
        config_path = (pathlib.Path(__file__).parent.parent / 'integration_tests_video' / '2730cfc6.webm').as_posix()
        request = {}
        with open(config_path, 'rb') as video:
            request['VideoBody'] = base64.b64encode(video.read()).decode('utf-8')

        request['SearchPhraseIdentifiers'] = ["error", "exception"]
        request['URLContains'] = ["wpadmin", "force.com"]
        request['TextContains'] = ["Contact Form", "MariaDB"]

        json_encoded_request = json.dumps(request)
        result = process_request(json_encoded_request)

        self.assertIn('Contact Form System DmlException: Insert failed. First exception on row O; first erro Tag No '
                      'eae eh ea [LastName', result['SearchPhrasesFound'][0])

        self.assertTrue(result['URLContainsResults']['force.com'])

        self.assertTrue(result['TextContainsResults']['Contact Form'])
