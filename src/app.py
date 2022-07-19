import os
import sqlite3
import asyncio
import logging
import aiohttp
import json

from decimal import Decimal
from datetime import datetime
from aiohttp import web
from claim.claim import DonationTokenClaim
from claim.claim_storage import ClaimStorage, SqlLiteClaimStorage
from create_claim.create_claim_handler import CreateClaimApi, CreateClaimHandler

from get_env import get_env

from lnbits import (
    AmountSats,
    LnBitsApi,
    LnBitsApiKey,
    LnBitsCallbackData,
)
from sign.sign import DonationKeySigner
from success_callback.callback_handler import CallbackHandler

root = logging.getLogger()
root.setLevel(logging.DEBUG)


private_key_path = get_env("PRIVATE_KEY")
domain = get_env("DOMAIN")
ln_bits_api_key = LnBitsApiKey(get_env("LN_BITS_API_KEY"))
ln_bits_url = LnBitsApiKey(get_env("LN_BITS_URL"))
sats_amount = AmountSats(Decimal(get_env("SATS_AMOUNT")))
web_server_port = get_env("PORT")

if not os.path.exists(private_key_path):
    raise Exception(f"Private key {private_key_path} not found")

URL_CLAIM = "/api/key/claim"
URL_PAYMENT_SUCCESS_CALLBACK = "/api/key/payment-success-callback"

dirname = os.path.dirname(__file__)


async def run() -> None:
    donation_key_signer = DonationKeySigner(private_key_path)

    routes = web.RouteTableDef()
    db_path = f"{dirname}/database.db"
    is_first_start = os.path.exists(db_path)
    sql_lite_connection = sqlite3.connect(db_path)
    sql_lite_storage = SqlLiteClaimStorage(datetime.now, sql_lite_connection)

    if not is_first_start:
        logging.info(f"Fresh database, creating tables.")
        sql_lite_storage.create_tables()

    claim_storage: ClaimStorage = sql_lite_storage

    session = aiohttp.ClientSession()

    ln_bits_api = LnBitsApi(session, ln_bits_url, ln_bits_api_key)

    callback_handler = CallbackHandler(claim_storage, ln_bits_api, donation_key_signer)
    create_claim_handler = CreateClaimHandler(claim_storage, ln_bits_api)

    create_claim_semaphore = asyncio.Semaphore(1)

    @routes.post("/")
    async def root(request: web.Request) -> web.Response:

        return web.Response(body=json.dumps({"ok": True}))

    @routes.post(URL_CLAIM)
    async def create_claim(request: web.Request) -> web.Response:
        json_request = await request.json()
        logging.info(f"WebServer: POST {URL_CLAIM}, body: {json_request}")
        create_claim_api = CreateClaimApi(**json_request)

        async with create_claim_semaphore:
            lnurl = await create_claim_handler.handle(create_claim_api, sats_amount)

        return web.Response(body=json.dumps({"lnurl": lnurl}))

    lnurl_payment_success_callback_semaphore = asyncio.Semaphore(1)

    @routes.post(URL_PAYMENT_SUCCESS_CALLBACK)
    async def lnurl_payment_success_callback(request: web.Request) -> web.Response:
        json_request = await request.json()
        logging.info(f"WebServer: POST {URL_CLAIM}, body: {json_request}")
        callback_data = LnBitsCallbackData(**json_request)

        async with lnurl_payment_success_callback_semaphore:
            await callback_handler.handle(callback_data, sats_amount)

        return web.Response(body="", status=200)

    @routes.get(URL_CLAIM + "/{claim}")
    async def get_claim_status(request: web.Request) -> web.Response:
        claim = DonationTokenClaim(request.match_info["claim"])
        key, status = claim_storage.get_claim_status(claim)

        if status is None:
            return web.Response(status=404)

        return web.Response(body=json.dumps({"key": key, "status": status}), status=200)

    app = web.Application()
    app.add_routes(routes)

    try:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=web_server_port)
        await site.start()
        logging.info(f"Server running at port: {web_server_port}")
        while True:
            await asyncio.sleep(10)
        # await runner.cleanup()
    finally:
        await session.close()
        sql_lite_connection.close()


asyncio.run(run())
