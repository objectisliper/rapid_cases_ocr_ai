from aiohttp import web
from .managers import process_request


class HealthcheckEndpoint(web.View):
    async def get(self):
        return web.json_response({'result': 1})


class ProcessEndpoint(web.View):
    async def post(self):
        # check ruleset
        request_body = await self.request.read()
        return web.json_response(process_request(request_body))
