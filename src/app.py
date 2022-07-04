import asyncio
import os
import logging
from weakref import WeakMethod
import aiohttp
import json

from decimal import Decimal
from typing import NewType, Tuple
from aiohttp import web
from pydantic import BaseModel
from claim import DonationTokenClaim

from claim_storage import ClaimStorage, InMemoryClaimStorage

from lnbits import (
    AmountSats,
    LnBitsApi,
    LnBitsApiKey,
    LnBitsCallbackData,
    LnBitsPaymentLinkId,
    LnUrl,
    PaymentHash,
)
from payment_callback_validation import payment_callback_validation
from sign import sign
from validate_payment_by_hash import validate_payment_by_hash

root = logging.getLogger()
root.setLevel(logging.DEBUG)


def get_env(name: str) -> str:
    raw = os.environ.get(name)
    if raw is None:
        raise Exception("ENV variable '" + name + "' is missing")

    return raw


private_key_path = get_env("PRIVATE_KEY")
domain = get_env("DOMAIN")
ln_bits_api_key = LnBitsApiKey(get_env("LN_BITS_API_KEY"))
ln_bits_url = LnBitsApiKey(get_env("LN_BITS_URL"))
sats_amount = AmountSats(Decimal(get_env("SATS_AMOUNT")))
web_server_port = 8080


URL_CLAIM = "/api/donation/key/claim"
URL_PAYMENT_SUCCESS_CALLBACK = "/api/donation/key/payment-success-callback"


async def run() -> None:
    claim_storage: ClaimStorage = InMemoryClaimStorage()
    routes = web.RouteTableDef()

    ln_bits_api = LnBitsApi(aiohttp.ClientSession(), ln_bits_url, ln_bits_api_key)

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
        claim = claim_storage.get_claim_by_id(callback_data.lnurlp)

        if claim is None:
            logging.error(f"WebServer: CLAIM NOT FOUND! for body: {json_request}")
            return web.Response(body="", status=200)

        callback_validation = payment_callback_validation(callback_data, sats_amount)
        if callback_validation is not None:
            claim_storage.change_status(claim, callback_validation)
            return web.Response(body="", status=200)

        payment_hash = PaymentHash(json_request["payment_hash"])
        payment = await ln_bits_api.get_payment(payment_hash)

        payment_validation = validate_payment_by_hash(payment, callback_data.lnurlp, sats_amount)
        if payment_validation is not None:
            claim_storage.change_status(claim, payment_validation)
            return web.Response(body="", status=200)

        claim_storage.change_status(claim, f"Sucessfully claimed")
        claim_storage.change_status(claim, f"KEY: {sign(private_key_path, claim)}")

        return web.Response(body="", status=200)

    @routes.get(URL_CLAIM + "/{claim}")
    async def get_claim_status(request: web.Request) -> web.Response:
        claim = DonationTokenClaim(request.match_info["claim"])
        status = claim_storage.get_claim_status(claim)

        if status is None:
            return web.Response(status=404)

        return web.Response(body=json.dumps({"status": status}), status=200)

    app = web.Application()
    app.add_routes(routes)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", web_server_port)
    await site.start()
    logging.info(f"Server running at port: {web_server_port}")
    while True:
        await asyncio.sleep(10)
    # await runner.cleanup()


asyncio.run(run())
