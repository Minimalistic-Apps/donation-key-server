import os
import sqlite3
import pytest

from datetime import datetime

from claim.claim import DonationTokenClaim
from claim.claim_storage import ClaimAlreadyExistsException, ClaimStorage, SqlLiteClaimStorage

from claim.donation_key import DonationKey
from lnbits import LnBitsPaymentLinkId, PaymentHash

dirname = os.path.dirname(__file__)

claim_A = DonationTokenClaim("A")
link_1 = LnBitsPaymentLinkId(1)

link_2 = LnBitsPaymentLinkId(2)


def test_now() -> datetime:
    return datetime.fromtimestamp(0)


def create_fresh_sql_live_storage() -> SqlLiteClaimStorage:
    db_path = f"{dirname}/test_database.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    sql_lite_connection = sqlite3.connect(db_path)
    storage = SqlLiteClaimStorage(test_now, sql_lite_connection)
    storage.create_tables()

    return storage


@pytest.mark.parametrize(
    "storage",
    [create_fresh_sql_live_storage()],
)
def test_storage_happy_path(storage: ClaimStorage) -> None:
    # User creates claim
    storage.add(claim_A, link_1)
    assert storage.get_claim_status(claim_A) == (None, ["[1970-01-01T01:00:00] Claim created, waiting for payment..."])
    assert storage.get_claim_by_id(link_1) == claim_A
    assert storage.get_claim_by_id(link_2) is None

    # User pays the LNURL and payment hash and donation key are stored
    storage.save_success(claim_A, PaymentHash("AAA"), DonationKey("A/XY12=="))

    assert storage.is_payment_hashed_used(PaymentHash("AAA")) is True
    assert storage.get_claim_status(claim_A) == (
        "A/XY12==",
        [
            "[1970-01-01T01:00:00] Claim created, waiting for payment...",
            "[1970-01-01T01:00:00] Sucessfully claimed.",
        ],
    )
    assert storage.is_payment_hashed_used(PaymentHash("BBB")) is False

    # User tries to create same claim again (with new link)
    # the previous link is prvied in the exception!
    try:
        storage.add(claim_A, link_2)
        assert False, "Should raise ClaimAlreadyExistsException"
    except ClaimAlreadyExistsException as e:
        assert e.existing_payment_link_id() == link_1
