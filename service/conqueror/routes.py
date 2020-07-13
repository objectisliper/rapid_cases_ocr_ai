from aiohttp import web

from .views import HealthcheckEndpoint, ProcessEndpoint

url_list = [
        web.view("/healthcheck/", HealthcheckEndpoint),
        web.view("/process/", ProcessEndpoint),
    ]
