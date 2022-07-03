from datetime import datetime
from abc import ABCMeta, abstractmethod
from typing import Dict, List, Optional
from claim import DonationTokenClaim

from lnbits import LnBitsPaymentLinkId


class ClaimStorage(metaclass=ABCMeta):
    @abstractmethod
    def add(self, claim: DonationTokenClaim, id: LnBitsPaymentLinkId) -> None:
        raise NotImplementedError()

    @abstractmethod
    def change_status(self, claim: DonationTokenClaim, status: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def get_claim_by_id(self, id: LnBitsPaymentLinkId) -> Optional[DonationTokenClaim]:
        raise NotImplementedError()

    @abstractmethod
    def get_claim_status(self, claim: DonationTokenClaim) -> Optional[List[str]]:
        raise NotImplementedError()


class InMemoryClaimStorage(ClaimStorage):
    _ids: Dict[LnBitsPaymentLinkId, DonationTokenClaim] = {}
    _status: Dict[DonationTokenClaim, List[str]] = {}

    def add(self, claim: DonationTokenClaim, id: LnBitsPaymentLinkId) -> None:
        self._ids[id] = claim
        self._status[claim] = []
        self.change_status(claim, "Claim created, waiting for payment...")

    def change_status(self, claim: DonationTokenClaim, status: str) -> None:
        self._status[claim].append(f"[{datetime.now().isoformat()}] {status}")

    def get_claim_by_id(self, id: LnBitsPaymentLinkId) -> Optional[DonationTokenClaim]:
        return self._ids.get(id, None)

    def get_claim_status(self, claim: DonationTokenClaim) -> Optional[List[str]]:
        return self._status.get(claim, None)
