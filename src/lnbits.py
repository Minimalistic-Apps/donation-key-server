from decimal import Decimal
import logging
from typing import Dict, NewType
import aiohttp
from pydantic import BaseModel


LnUrl = NewType("LnUrl", str)
LnBitsApiKey = NewType("LnBitsApiKey", str)
LnBitsPaymentLinkId = NewType("LnBitsPaymentLinkId", int)
AmountSats = NewType("AmountSats", Decimal)
PaymentHash = NewType("PaymentHash", str)


class LnBitsPaymentDetailsExtra(BaseModel):
    tag: str
    link: LnBitsPaymentLinkId
    comment: str
    extra: str
    wh_status: int


class LnBitsPaymentDetails(BaseModel):
    checking_id: str
    pending: bool
    amount: int
    fee: int
    memo: str
    time: int
    bolt11: str
    preimage: str
    payment_hash: str
    extra: LnBitsPaymentDetailsExtra
    wallet_id: str
    # webhook: any
    # webhook_status: any


class LnBitsPayment(BaseModel):
    paid: bool
    preimage: str
    details: LnBitsPaymentDetails


class LnBitsCallbackData(BaseModel):
    payment_hash: PaymentHash
    payment_request: str
    amount: AmountSats
    comment: str
    lnurlp: LnBitsPaymentLinkId


class LnBitsApi:
    def __init__(self, session: aiohttp.ClientSession, baseUrl: str, api_key: LnBitsApiKey) -> None:
        self._session = session
        self._baseUrl = baseUrl
        self._api_key = api_key

    async def create_pay_link(
        self,
        amount: AmountSats,
        description: str,
        callback_url: str,
    ) -> LnBitsPaymentLinkId:
        url = f"{self._baseUrl}/lnurlp/api/v1/links"

        request_body = {
            "description": description,
            # "amount": amount,
            "max": int(amount),  # min=max for fixed amount
            "min": int(amount),
            "comment_chars": 0,
            "webhook_url": callback_url,
        }

        async with self._session.post(url, headers={"X-Api-Key": self._api_key}, json=request_body) as response:
            result = await response.json()
            logging.info(f"Outgoing >>: {url}, Reqult: {result}")

            return LnBitsPaymentLinkId(int(result["id"]))

    async def get_payment_link(self, payId: LnBitsPaymentLinkId) -> LnUrl:
        url = f"{self._baseUrl}/lnurlp/api/v1/links/{payId}"

        async with self._session.get(url, headers={"X-Api-Key": self._api_key}) as response:
            result = await response.json()
            logging.info(f"Outgoing >> URL: {url}, Result: {result}")

            return LnUrl(result["lnurl"])

    async def get_payment(self, payment_hash: PaymentHash) -> LnBitsPayment:
        url = f"{self._baseUrl}/api/v1/payments/{payment_hash}"

        async with self._session.get(url, headers={"X-Api-Key": self._api_key}) as response:
            result = await response.json()
            logging.info(f"Outgoing >> URL: {url}, Result: {result}")

            return LnBitsPayment(**result)
