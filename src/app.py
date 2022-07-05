import os
import sqlite3
import asyncio
import logging
import aiohttp
import json

from decimal import Decimal
from datetime import datetime
from typing import Tuple
from aiohttp import web
from pydantic import BaseModel
from claim.claim import DonationTokenClaim
from claim.claim_storage import ClaimStorage, SqlLiteClaimStorage

from get_env import get_env

from lnbits import (
    AmountSats,
    LnBitsApi,
    LnBitsApiKey,
    LnBitsCallbackData,
    LnBitsPaymentLinkId,
    LnUrl,
    PaymentHash,
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
web_server_port = 8080

if not os.path.exists(private_key_path):
    raise Exception(f"Private key {private_key_path} not found")

URL_CLAIM = "/api/donation/key/claim"
URL_PAYMENT_SUCCESS_CALLBACK = "/api/donation/key/payment-success-callback"

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

    async def do_create_pay_link(
        amount: AmountSats,
        claim: DonationTokenClaim,
        callback_url: str,
    ) -> Tuple[LnBitsPaymentLinkId, LnUrl]:
        response = await ln_bits_api.create_pay_link(amount, claim, callback_url)
        created_payment_link = await ln_bits_api.get_payment_link(response.id)

        return created_payment_link.id, created_payment_link.lnurl

    class CreateClaimApi(BaseModel):
        claim: DonationTokenClaim

    @routes.post(URL_CLAIM)
    async def create_claim(request: web.Request) -> web.Response:
        json_request = await request.json()
        logging.info(f"WebServer: POST {URL_CLAIM}, body: {json_request}")
        create_claim_api = CreateClaimApi(**json_request)

        if create_claim_api.claim is None:
            # Todo: validate claim (lenght, format, ....)
            return web.Response(body=json.dumps({"errors": ["'claim' is missing in the body "]}))

        id, lnurl = await do_create_pay_link(
            sats_amount,
            create_claim_api.claim,
            "https://webhook.site/e48b88ce-b07d-43b0-b377-78726d444539"
            # domain + URL_PAYMENT_SUCCESS_CALLBACK,
        )

        claim_storage.add(create_claim_api.claim, id)

        return web.Response(body=json.dumps({"lnurl": lnurl}))

    @routes.post(URL_PAYMENT_SUCCESS_CALLBACK)
    async def lnurl_payment_success_callback(request: web.Request) -> web.Response:
        json_request = await request.json()
        logging.info(f"WebServer: POST {URL_CLAIM}, body: {json_request}")
        callback_data = LnBitsCallbackData(**json_request)
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
        site = web.TCPSite(runner, "localhost", web_server_port)
        await site.start()
        logging.info(f"Server running at port: {web_server_port}")
        while True:
            await asyncio.sleep(10)
        # await runner.cleanup()
    finally:
        await session.close()
        sql_lite_connection.close()


asyncio.run(run())
