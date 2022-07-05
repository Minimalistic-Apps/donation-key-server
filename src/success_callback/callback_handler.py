import logging

from rsa import sign

from claim.claim_storage import ClaimStorage
from claim.statuses import PAYMENT_HASH_USED_STATUS
from lnbits import AmountSats, LnBitsApi, LnBitsCallbackData
from sign.sign import DonationKeySigner
from success_callback.payment_callback_validation import payment_callback_validation
from success_callback.validate_payment_by_hash import validate_payment_by_hash


class CallbackHandler:
    def __init__(
        self, claim_storage: ClaimStorage, ln_bits_api: LnBitsApi, donation_key_signer: DonationKeySigner
    ) -> None:
        self._claim_storage = claim_storage
        self._ln_bits_api = ln_bits_api
        self._donation_key_signer = donation_key_signer

    async def handle(self, callback_data: LnBitsCallbackData, expected_sats_amount: AmountSats) -> None:
        claim = self._claim_storage.get_claim_by_id(callback_data.lnurlp)

        if claim is None:
            logging.error(f"WebServer: CLAIM NOT FOUND! for id: {callback_data.lnurlp}")
            return

        callback_validation = payment_callback_validation(callback_data, expected_sats_amount)
        if callback_validation is not None:
            self._claim_storage.change_status(claim, callback_validation)
            return

        payment = await self._ln_bits_api.get_payment(callback_data.payment_hash)

        payment_validation = validate_payment_by_hash(payment, callback_data.lnurlp, expected_sats_amount)
        if payment_validation is not None:
            self._claim_storage.change_status(claim, payment_validation)
            return

        if self._claim_storage.is_payment_hashed_used(callback_data.payment_hash):
            self._claim_storage.change_status(claim, PAYMENT_HASH_USED_STATUS)
            return

        self._claim_storage.save_success(claim, callback_data.payment_hash, self._donation_key_signer.sign(claim))

        return
