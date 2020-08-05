import base64
import json
import zlib

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app import celery_broker
from service.conqueror.db_models import select_uploaded_jobs, select_job_by_id
from service.conqueror.managers import process_request


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
    with open(job.local_path, 'rb') as video:
        data['VideoBody'] = base64.b64encode(video.read()).decode('utf-8')

    data['SearchPhraseIdentifiers'] = ["error", "exception"]
    data['URLContains'] = ["wpadmin", "wordpress.com"]
    data['TextContains'] = ["MySQL", "MariaDB"]
    json_encoded_request = json.dumps(data)
    result = process_request(json_encoded_request)
    print('end processing')
    job.job_processed('\n '.join(result.get('SearchPhrasesFound')))


celery_broker.add_periodic_task(schedule=120.0, sig=get_videos_to_process.s(), queue='recognizer_scheduling')