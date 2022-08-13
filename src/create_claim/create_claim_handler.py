from asyncio.log import logger
from typing import Tuple
from pydantic import BaseModel

from claim.claim import DonationTokenClaim
from claim.claim_storage import ClaimStorage
from lnbits import AmountSats, LnBitsApi, LnBitsPaymentLinkId, LnUrl
from settings import DOMAIN, URL_PAYMENT_SUCCESS_CALLBACK


class CreateClaimApi(BaseModel):
    claim: DonationTokenClaim


class CreateClaimHandler:
    def __init__(self, claim_storage: ClaimStorage, ln_bits_api: LnBitsApi) -> None:
        self._claim_storage = claim_storage
        self._ln_bits_api = ln_bits_api

    async def _do_create_pay_link(
        self,
        amount: AmountSats,
        claim: DonationTokenClaim,
        callback_url: str,
    ) -> Tuple[LnBitsPaymentLinkId, LnUrl]:
        response = await self._ln_bits_api.create_pay_link(amount, claim, callback_url)
        created_payment_link = await self._ln_bits_api.get_payment_link(response.id)

        return created_payment_link.id, created_payment_link.lnurl

    async def handle(self, create_claim_api: CreateClaimApi, expected_sats_amount: AmountSats) -> LnUrl:
        existing_payment_link_id = self._claim_storage.get_claim(create_claim_api.claim)

        if existing_payment_link_id is not None:
            logger.warning(f"Claim ${create_claim_api.claim} already has an payment link {existing_payment_link_id}")
            existing_payment_link = await self._ln_bits_api.get_payment_link(existing_payment_link_id)
            return existing_payment_link.lnurl

        id, lnurl = await self._do_create_pay_link(
            expected_sats_amount,
            create_claim_api.claim,
            DOMAIN + URL_PAYMENT_SUCCESS_CALLBACK,
        )

        self._claim_storage.add(create_claim_api.claim, id)

        return lnurl
