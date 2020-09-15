import argparse
import logging

from aiohttp import web

from service.conqueror.routes import url_list
from service.conqueror.settings.local import PORT, DEBUG

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
