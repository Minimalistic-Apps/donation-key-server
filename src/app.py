import os
import logging
import aiohttp
import json

from decimal import Decimal
from typing import NewType, Tuple
from aiohttp import web

from claim_storage import ClaimStorage, InMemoryClaimStorage

from lnbits import (
    AmountSats,
    LnBitsApi,
    LnBitsApiKey,
    LnBitsPaymentLinkId,
    LnUrl,
)
from sign import sign

root = logging.getLogger()
root.setLevel(logging.DEBUG)

DonationTokenClaim = NewType("DonationTokenClaim", str)


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


URL_CLAIM = "/api/donation/key/claim"
URL_PAYMENT_SUCCESS_CALLBACK = "/api/donation/key/payment-success-callback"


claim_storage: ClaimStorage = InMemoryClaimStorage()
routes = web.RouteTableDef()

ln_bits_api = LnBitsApi(aiohttp.ClientSession(), ln_bits_url, ln_bits_api_key)


async def do_create_pay_link(
    amount: AmountSats,
    claim: DonationTokenClaim,
    callback_url: str,
) -> Tuple[int, LnUrl]:
    id = await ln_bits_api.create_pay_link(amount, claim, callback_url)

    return id, await ln_bits_api.get_payment_link(id)


@routes.post(URL_CLAIM)
async def donation_key_claim(request: web.Request) -> web.Response:
    json_request = await request.json()
    logging.info(f"WebServer: POST {URL_CLAIM}, body: {json_request}")

    if json_request["claim"] is None:
        # Todo: validate claim (lenght, format, ....)
        return web.Response(body=json.dumps({"errors": ["'claim' is missing in the body "]}))

    claim = DonationTokenClaim(json_request["claim"])
    id, lnurl = await do_create_pay_link(
        sats_amount,
        claim,
        domain + URL_PAYMENT_SUCCESS_CALLBACK,
    )

    claim_storage.add(claim, id, lnurl)

    return web.Response(body=json.dumps({"lnurl": lnurl}))


@routes.post(URL_PAYMENT_SUCCESS_CALLBACK)
async def lnurl_payment_success_callback(request: web.Request) -> web.Response:
    # {
    #     "payment_hash": "0886....",
    #     "payment_request": "lnbc100n1p3.....",
    #     "amount": 10000,
    #     "comment": "",
    #     "lnurlp": 1944  # <-- This is ID of the Pay Link
    # }
    json_request = await request.json()
    logging.info(f"WebServer: POST {URL_CLAIM}, body: {json_request}")

    id = LnBitsPaymentLinkId(int(json_request["lnurlp"]))
    amount = AmountSats(Decimal(json_request["amount"]))

    claim = claim_storage.get_claim_by_id(id)

    if claim is None:
        logging.error(f"WebServer: CLAIM NOT FOUND! for body: {json_request}")
        return web.Response(body="", status=200)

    if amount < sats_amount:
        claim_storage.change_status(
            claim, f"Amount send ${json_request.amount} is less then ${sats_amount}, please contact suport for refund"
        )
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
web.run_app(app)
