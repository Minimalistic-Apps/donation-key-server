from decimal import Decimal
import logging
from typing import Dict, NewType, Optional, Union
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
    comment: Optional[str]
    extra: str


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
    comment: Optional[str]
    lnurlp: LnBitsPaymentLinkId


class LnBitsPaymentLinkCreate(BaseModel):
    id: LnBitsPaymentLinkId
    wallet: str
    description: str
    min: float
    max: float
    served_meta: int
    served_pr: int
    webhook_url: Optional[str]
    # success_text: None
    # success_url: None
    # currency: None
    comment_chars: int
    # fiat_base_multiplier: int # no present for all versions
    # lnurl: any For some reason lnbit returns {} insetad of lnurl


class LnBitsPaymentLinkGet(LnBitsPaymentLinkCreate):
    lnurl: LnUrl


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
    ) -> LnBitsPaymentLinkCreate:
        url = f"{self._baseUrl}/lnurlp/api/v1/links"

        request_body = {
            "description": description,
            # "amount": amount,
            "max": int(amount),  # min=max for fixed amount
            "min": int(amount),
            "comment_chars": 0,
            "webhook_url": callback_url,
            "success_text": "Thank you for your donation. Go back to the app!",
            # This causes 500 from lnbits (bug there?)
            # "success_url": "minapps-priceconvertor://success",
        }

        async with self._session.post(url, headers={"X-Api-Key": self._api_key}, json=request_body) as response:
            logging.info(f"Outgoing >>: POST {url}, Result: {response.status} {await response.text()}")
            result = await response.json()

            return LnBitsPaymentLinkCreate(**result)

    async def get_payment_link(self, payId: LnBitsPaymentLinkId) -> LnBitsPaymentLinkGet:
        url = f"{self._baseUrl}/lnurlp/api/v1/links/{payId}"

        async with self._session.get(url, headers={"X-Api-Key": self._api_key}) as response:
            logging.info(f"Outgoing >>: GET {url}, Result: {response.status} {await response.text()}")
            result = await response.json()

            return LnBitsPaymentLinkGet(**result)

    async def get_payment(self, payment_hash: PaymentHash) -> LnBitsPayment:
        url = f"{self._baseUrl}/api/v1/payments/{payment_hash}"

        async with self._session.get(url, headers={"X-Api-Key": self._api_key}) as response:
            logging.info(f"Outgoing >>: POST {url}, Result: {response.status} {await response.text()}")
            result = await response.json()

            return LnBitsPayment(**result)
