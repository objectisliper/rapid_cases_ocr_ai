import argparse
import logging

from aiohttp import web
from celery import Celery
from kombu import Queue, Exchange

from service.conqueror.routes import url_list
from service.conqueror.settings.local import PORT, DEBUG, CELERY_BROKER_URL

celery_broker = Celery('tasks', broker=CELERY_BROKER_URL)

recognizer_scheduling_exchange = Exchange('recognizer_scheduling', type='direct')

recognizer_process_video_exchange = Exchange('recognizer_process_video', type='direct')

celery_broker.conf.task_queues = (
    Queue('recognizer_scheduling', recognizer_scheduling_exchange),
    Queue('recognizer_process_video', recognizer_process_video_exchange)
)

celery_broker.conf.timezone = 'UTC'

celery_broker.conf.task_routes = {'service.conqueror.scheduling.process_video': {'queue': 'recognizer_process_video'}}

parser = argparse.ArgumentParser(description="aiohttp server example")
parser.add_argument('--path')
parser.add_argument('--port')
parser.add_argument('--live', action='store_true')


def make_app():
    app = web.Application()

    app.router.add_routes(url_list)

    return app


if __name__ == "__main__":
    app = make_app()
    args = parser.parse_args()

    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    if args.live:
        web.run_app(app, path=args.path, port=args.port)
    else:
        web.run_app(app, host="127.0.0.1", port=PORT)
