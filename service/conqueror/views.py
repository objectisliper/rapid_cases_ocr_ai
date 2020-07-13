"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Web service endpoint definitions

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""

from aiohttp import web
from .managers import process_request


class HealthcheckEndpoint(web.View):
    async def get(self):
        return {'result': 1}


class ProcessEndpoint(web.View):
    """
    Main endpoint for processing video data
    and returning the text required
    """
    async def post(self):
        # check ruleset
        return process_request(self.request)
