from datetime import datetime
from abc import ABCMeta, abstractmethod
from sqlite3 import Connection
from typing import Callable, Dict, List, Optional

from claim.claim import DonationTokenClaim
from claim.donation_key import DonationKey

from lnbits import LnBitsPaymentLinkId, PaymentHash


class ClaimStorage(metaclass=ABCMeta):
    @abstractmethod
    def add(self, claim: DonationTokenClaim, id: LnBitsPaymentLinkId) -> None:
        raise NotImplementedError()

    @abstractmethod
    def change_status(self, claim: DonationTokenClaim, status: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def save_success(self, claim: DonationTokenClaim, payment_hash: PaymentHash, donation_key: DonationKey) -> None:
        raise NotImplementedError()

    @abstractmethod
    def get_claim_by_id(self, id: LnBitsPaymentLinkId) -> Optional[DonationTokenClaim]:
        raise NotImplementedError()

    @abstractmethod
    def get_claim_status(self, claim: DonationTokenClaim) -> Optional[List[str]]:
        raise NotImplementedError()

    @abstractmethod
    def is_payment_hashed_used(self, payment_hash: PaymentHash) -> bool:
        raise NotImplementedError()


CREATED_STATUS = "Claim created, waiting for payment..."
SUCCESS_STATUS = "Sucessfully claimed."


class InMemoryClaimStorage(ClaimStorage):
    _ids: Dict[LnBitsPaymentLinkId, DonationTokenClaim] = {}
    _status: Dict[DonationTokenClaim, List[str]] = {}
    _used_hashes: Dict[PaymentHash, DonationTokenClaim] = {}

    def __init__(self, now_date_function: Callable[[], datetime]) -> None:
        self._now_date_function = now_date_function

    def add(self, claim: DonationTokenClaim, id: LnBitsPaymentLinkId) -> None:
        self._ids[id] = claim
        self._status[claim] = []
        self.change_status(claim, CREATED_STATUS)

    def change_status(self, claim: DonationTokenClaim, status: str) -> None:
        self._status[claim].append(f"[{self._now_date_function().isoformat()}] {status}")

    def get_claim_by_id(self, id: LnBitsPaymentLinkId) -> Optional[DonationTokenClaim]:
        return self._ids.get(id, None)

    def get_claim_status(self, claim: DonationTokenClaim) -> Optional[List[str]]:
        return self._status.get(claim, None)

    def save_success(self, claim: DonationTokenClaim, payment_hash: PaymentHash, donation_key: DonationKey) -> None:
        self._used_hashes[payment_hash] = claim
        self.change_status(claim, SUCCESS_STATUS)

    def is_payment_hashed_used(self, payment_hash: PaymentHash) -> bool:
        return self._used_hashes.get(payment_hash, None) != None


class SqlLiteClaimStorage(ClaimStorage):
    def __init__(self, now_date_function: Callable[[], datetime], connction: Connection) -> None:
        self._now_date_function = now_date_function
        self._connection = connction

    def create_tables(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE claims (
                claim text NOT NULL PRIMARY KEY, 
                lnbit_payment_link_id int NOT NULL,
                payment_hash text NULL UNIQUE,
                donation_key text NULL
            )
        """
        )
        self._connection.execute("CREATE INDEX claims_payment_hash ON claims (payment_hash)")
        self._connection.execute("CREATE INDEX claims_lnbit_payment_link_id ON claims (lnbit_payment_link_id)")
        self._connection.execute(
            """
            CREATE TABLE statuses (
                claim text NOT NULL, 
                created_at timestamp,
                status text NOT NULL
            )
        """
        )
        self._connection.execute("CREATE INDEX statuses_claim ON statuses (claim)")
        self._connection.commit()

    def add(self, claim: DonationTokenClaim, id: LnBitsPaymentLinkId) -> None:
        self._connection.execute("INSERT INTO claims (claim, lnbit_payment_link_id) VALUES (?, ?)", (claim, id))
        self._connection.commit()
        self.change_status(claim, CREATED_STATUS)

    def change_status(self, claim: DonationTokenClaim, status: str) -> None:
        self._connection.execute(
            "INSERT INTO statuses (claim, created_at, status) VALUES (?, ?, ?)",
            (claim, self._now_date_function().timestamp(), status),
        )
        self._connection.commit()

    def get_claim_by_id(self, id: LnBitsPaymentLinkId) -> Optional[DonationTokenClaim]:
        cur = self._connection.cursor()
        cur.execute(
            "SELECT claim FROM claims WHERE lnbit_payment_link_id = :lnbit_payment_link_id",
            {"lnbit_payment_link_id": id},
        )
        row = cur.fetchone()
        cur.close()

        if row is None:
            return None

        return DonationTokenClaim(row[0])

    def get_claim_status(self, claim: DonationTokenClaim) -> Optional[List[str]]:
        cur = self._connection.cursor()
        cur.execute("SELECT created_at, status FROM statuses WHERE claim = :claim", {"claim": claim})
        rows = cur.fetchall()
        cur.close()

        if rows is None:
            return None

        return [f"[{datetime.fromtimestamp(row[0]).isoformat()}] {row[1]}" for row in rows]

    def save_success(self, claim: DonationTokenClaim, payment_hash: PaymentHash, donation_key: DonationKey) -> None:
        self._connection.execute(
            "UPDATE claims SET payment_hash = ?, donation_key = ? WHERE claim = ?", (payment_hash, donation_key, claim)
        )
        self._connection.commit()
        self.change_status(claim, SUCCESS_STATUS)

    def is_payment_hashed_used(self, payment_hash: PaymentHash) -> bool:
        cur = self._connection.cursor()
        cur.execute("SELECT claim FROM claims WHERE payment_hash = :payment_hash", {"payment_hash": payment_hash})
        row = cur.fetchone()
        cur.close()

        return row is not None

    def dump(self) -> None:
        cur = self._connection.cursor()
        cur.execute("SELECT * FROM claims")
        rows = cur.fetchall()
        cur.close()
        print(rows)
