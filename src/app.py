import os
import sqlite3
import asyncio
import logging
import aiohttp
import json

from datetime import datetime
from aiohttp import web
from claim.claim import DonationTokenClaim
from claim.claim_storage import ClaimStorage, SqlLiteClaimStorage
from create_claim.create_claim_handler import CreateClaimApi, CreateClaimHandler

from lnbits import LnBitsApi, LnBitsCallbackData
from settings import (
    LN_BITS_API_KEY,
    LN_BITS_URL,
    PORT,
    PRIVATE_KEY,
    SATS_AMOUNT,
    URL_CLAIM,
    URL_PAYMENT_SUCCESS_CALLBACK,
)
from sign.sign import DonationKeySigner
from success_callback.callback_handler import CallbackHandler

root = logging.getLogger()
root.setLevel(logging.DEBUG)


if not os.path.exists(PRIVATE_KEY):
    raise Exception(f"Private key {PRIVATE_KEY} not found")

dirname = os.path.dirname(__file__)


async def run() -> None:
    donation_key_signer = DonationKeySigner(PRIVATE_KEY)

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

    ln_bits_api = LnBitsApi(session, LN_BITS_URL, LN_BITS_API_KEY)

    callback_handler = CallbackHandler(claim_storage, ln_bits_api, donation_key_signer)
    create_claim_handler = CreateClaimHandler(claim_storage, ln_bits_api)

    create_claim_semaphore = asyncio.Semaphore(1)

    @routes.get("/donation/api")
    async def root(request: web.Request) -> web.Response:
        return web.Response(body=json.dumps({"ok": True}))

    @routes.post(URL_CLAIM)
    async def create_claim(request: web.Request) -> web.Response:
        json_request = await request.json()
        logging.info(f"WebServer: POST {URL_CLAIM}, body: {json_request}")
        create_claim_api = CreateClaimApi(**json_request)

        async with create_claim_semaphore:
            lnurl = await create_claim_handler.handle(create_claim_api, SATS_AMOUNT)

        return web.Response(body=json.dumps({"lnurl": lnurl}))

    lnurl_payment_success_callback_semaphore = asyncio.Semaphore(1)

    @routes.post(URL_PAYMENT_SUCCESS_CALLBACK)
    async def lnurl_payment_success_callback(request: web.Request) -> web.Response:
        json_request = await request.json()
        logging.info(f"WebServer: POST {URL_CLAIM}, body: {json_request}")
        callback_data = LnBitsCallbackData(**json_request)

        async with lnurl_payment_success_callback_semaphore:
            await callback_handler.handle(callback_data, SATS_AMOUNT)

        return web.Response(body="", status=200)

    @routes.get(URL_CLAIM + "/{claim}")
    async def get_claim_status(request: web.Request) -> web.Response:
        claim = DonationTokenClaim(request.match_info["claim"])
        result = claim_storage.get_claim_status(claim)

        if result is None:
            return web.Response(status=404)

        key, status = result

        return web.Response(body=json.dumps({"key": key, "status": status}), status=200)

    app = web.Application()
    app.add_routes(routes)

    try:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
        await site.start()
        logging.info(f"Server running at port: {PORT}")
        while True:
            await asyncio.sleep(10)
        # await runner.cleanup()
    finally:
        await session.close()
        sql_lite_connection.close()


asyncio.run(run())
