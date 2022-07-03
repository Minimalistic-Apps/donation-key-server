import logging
from typing import Tuple
import aiohttp

from app_types import AmountSats, DonationTokenClaim, LnUrl, LnUrlToken

LN_BITS_DOMAIN = "https://lnurl.com"


async def do_create_pay_link(
    session: aiohttp.ClientSession,
    api_key: LnUrlToken,
    amount: AmountSats,
    claim: DonationTokenClaim,
    callback_url: str,
) -> Tuple[int, LnUrl]:
    id = await create_pay_link(session, api_key, amount, claim, callback_url)

    return id, await get_payment_link(session, api_key, id)


async def create_pay_link(
    session: aiohttp.ClientSession,
    api_key: LnUrlToken,
    amount: AmountSats,
    claim: DonationTokenClaim,
    callback_url: str,
) -> int:
    url = f"{LN_BITS_DOMAIN}/lnurlp/api/v1/links"

    request_body = {
        "description": claim,
        # "amount": amount,
        "max": int(amount),  # min=max for fixed amount
        "min": int(amount),
        "comment_chars": 0,
        "webhook_url": callback_url,
    }

    async with session.post(url, headers={"X-Api-Key": api_key}, json=request_body) as response:
        result = await response.json()

        # {
        #     "id": 1935,
        #     "wallet": "*******************",
        #     "description": "abc",
        #     "min": 10.0,
        #     "served_meta": 0,
        #     "served_pr": 0,
        #     "webhook_url": "https://example.com/api/donation/key/payment-success-callback",
        #     "success_text": None,
        #     "success_url": None,
        #     "currency": None,
        #     "comment_chars": 0,
        #     "max": 10.0,
        #     "fiat_base_multiplier": 100,
        #     "lnurl": {},
        # }

        logging.info(f"URL: {url}, Reqult: {result}")

        return int(result["id"])


async def get_payment_link(session: aiohttp.ClientSession, api_key: LnUrlToken, payId: int) -> LnUrl:
    url = f"{LN_BITS_DOMAIN}/lnurlp/api/v1/links/{payId}"

    async with session.get(url, headers={"X-Api-Key": api_key}) as response:
        result = await response.json()

        logging.info(f"URL: {url}, Result: {result}")

        return LnUrl(result["lnurl"])
