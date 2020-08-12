import base64
import json
import pathlib
import zlib
from unittest import TestCase
from unittest.mock import patch

from service.conqueror.db_models import JobModel, JobStorageTypes
from service.conqueror.scheduling import get_videos_to_process, process_video


class JobMock:
    Status = 'Uploaded'
    Storage_Name = 'Default'
    JobId = 1
    Local_File_Path = (pathlib.Path(__file__).parent.parent / 'integration_tests_video' / '7bbfc76b.mp4').as_posix()


class JobMockAmazon:
    Status = 'Uploaded'
    Storage_Name = JobStorageTypes.Amazon_S3.value
    JobId = 1
    Local_File_Path = (pathlib.Path(__file__).parent.parent / 'integration_tests_video' / '7bbfc76b.mp4').as_posix()


def get_expected_result_json():
    data = {}
    with open(JobMock.Local_File_Path, 'rb') as video:
        data['VideoBody'] = base64.b64encode(video.read()).decode('utf-8')

    data['SearchPhraseIdentifiers'] = ["error", "exception"]
    data['URLContains'] = ["wpadmin", "wordpress.com"]
    data['TextContains'] = ["MySQL", "MariaDB"]
    return json.dumps(data)


def get_expected_amazon_result_json():
    data = {}
    data['VideoBody'] = base64.b64encode('fdasffasf'.encode()).decode('utf-8')

    data['SearchPhraseIdentifiers'] = ["error", "exception"]
    data['URLContains'] = ["wpadmin", "wordpress.com"]
    data['TextContains'] = ["MySQL", "MariaDB"]
    return json.dumps(data)


class SchedulingTaskTestCase(TestCase):

    def setUp(self) -> None:
        pass

    @patch('service.conqueror.scheduling.process_video.delay')
    @patch.object(JobModel, 'job_start_processing')
    @patch('service.conqueror.scheduling.select_uploaded_jobs', return_value=[JobModel(JobMock)])
    def test_get_videos_to_process(self, select_uploaded_jobs, job_start_processing, process_video):
        get_videos_to_process()
        select_uploaded_jobs.assert_called_once()
        process_video.assert_called_once_with(JobMock.JobId)
        job_start_processing.assert_called_once()

    @patch('service.conqueror.scheduling.process_request', return_value={'SearchPhrasesFound': ['some text']})
    @patch.object(JobModel, 'job_processed')
    @patch('service.conqueror.scheduling.select_job_by_id', return_value=JobModel(JobMock))
    def test_process_video(self, select_job_by_id, job_processed, process_request):
        job_id = 1
        process_video(job_id)
        select_job_by_id.assert_called_once_with(job_id)
        process_request.assert_called_once_with(get_expected_result_json())
        job_processed.assert_called_once_with('some text')

    @patch('service.conqueror.scheduling.get_video_from_amazon_server', return_value='fdasffasf'.encode())
    @patch('service.conqueror.scheduling.process_request', return_value={'SearchPhrasesFound': ['some text']})
    @patch.object(JobModel, 'job_processed')
    @patch('service.conqueror.scheduling.select_job_by_id', return_value=JobModel(JobMockAmazon))
    def test_process_amazon_video(self, select_job_by_id, job_processed, process_request, get_video_from_amazon_server):
        job_id = 1
        process_video(job_id)
        select_job_by_id.assert_called_once_with(job_id)
        process_request.assert_called_once_with(get_expected_amazon_result_json())
        job_processed.assert_called_once_with('some text')
        get_video_from_amazon_server.assert_called_once_with(job_id)
