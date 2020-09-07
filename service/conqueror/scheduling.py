import base64
import json

from app import celery_broker
from service.conqueror.db_models import select_uploaded_jobs, select_job_by_id, JobStorageTypes
from service.conqueror.managers import process_request
from service.conqueror.utils import get_video_from_amazon_server, FileNotFoundException


@celery_broker.task
def get_videos_to_process():
    jobs = select_uploaded_jobs()
    for job in jobs:
        process_video.delay(job.id)
        job.job_start_processing()


@celery_broker.task
def process_video(job_id):
    job = select_job_by_id(job_id)
    data = {}
    try:
        data['VideoBody'] = base64.b64encode(get_video_from_amazon_server(job_id)).decode('utf-8')
    except FileNotFoundException as e:
        job.exception_catched(str(e))
        raise e

    data['SearchPhraseIdentifiers'] = job.search_phrases
    data['URLContains'] = job.url_contains
    data['TextContains'] = job.text_contains
    json_encoded_request = json.dumps(data)
    try:
        result = process_request(json_encoded_request)
    except Exception as e:
        job.exception_catched(str(e))
        raise e
    print('end processing')
    print(result)
    job.job_processed(json.dumps(result))


celery_broker.add_periodic_task(schedule=1.0, sig=get_videos_to_process.s(), queue='recognizer_scheduling')
