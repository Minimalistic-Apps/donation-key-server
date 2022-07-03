from cmath import log
from decimal import Decimal
import logging
from typing import Dict, NewType, Optional, Tuple
import aiohttp
from aiohttp import web
import os
import json

from lnbits import (
    AmountSats,
    LnBitsApi,
    LnBitsApiKey,
    LnBitsPaymentLinkId,
    LnUrl,
)
from utils import dict_key_by_value


root = logging.getLogger()
root.setLevel(logging.DEBUG)

DonationTokenClaim = NewType("DonationTokenClaim", str)


def get_env(name: str) -> str:
    raw = os.environ.get(name)
    if raw is None:
        raise Exception("ENV variable '" + name + "' is missing")

    return raw


domain = get_env("DOMAIN")
ln_bits_api_key = LnBitsApiKey(get_env("LN_BITS_API_KEY"))
ln_bits_url = LnBitsApiKey(get_env("LN_BITS_URL"))
sats_amount = AmountSats(Decimal(get_env("SATS_AMOUNT")))


URL_CLAIM = "/api/donation/key/claim"
URL_PAYMENT_SUCCESS_CALLBACK = "/api/donation/key/payment-success-callback"


class ClaimStorage:
    _lnurls: Dict[DonationTokenClaim, LnUrl] = {}
    _ids: Dict[DonationTokenClaim, int] = {}

    _status: Dict[DonationTokenClaim, str] = {}

    def add(self, claim: DonationTokenClaim, id: int, ln_url: LnUrl) -> None:
        self._lnurls[claim] = ln_url
        self._ids[claim] = id
        self._status[claim] = "Waiting for payment"

    def change_status(self, claim: DonationTokenClaim, status: str) -> None:
        self._status[claim] = status

    def get_claim_by_id(self, id: int) -> Optional[DonationTokenClaim]:
        return dict_key_by_value(self._ids, id)


claim_stroage = ClaimStorage()
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

    claim_stroage.add(claim, id, lnurl)

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

    claim = claim_stroage.get_claim_by_id(id)

    if claim is None:
        logging.error(f"WebServer: CLAIM NOT FOUND! for body: {json_request}")
        return web.Response(body="", status=200)

    if amount < sats_amount:
        claim_stroage.change_status(
            claim, f"Amount send ${json_request.amount} is less then ${sats_amount}, please contact suport for refund"
        )
        return web.Response(body="", status=200)

    claim_stroage.change_status(claim, json_request.payment_request)

    return web.Response(body="", status=200)


app = web.Application()
app.add_routes(routes)
web.run_app(app)
