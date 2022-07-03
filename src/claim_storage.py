from datetime import datetime
from abc import ABCMeta, abstractmethod
from typing import Dict, List, Optional
from utils import dict_key_by_value

from lnbits import LnUrl
from app import DonationTokenClaim

class ClaimStorage(metaclass=ABCMeta):
    @abstractmethod
    def add(self, claim: DonationTokenClaim, id: int, ln_url: LnUrl) -> None:
        raise NotImplementedError()

    @abstractmethod
    def change_status(self, claim: DonationTokenClaim, status: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def get_claim_by_id(self, id: int) -> Optional[DonationTokenClaim]:
        raise NotImplementedError()


class InMemoryClaimStorage(ClaimStorage):
    _lnurls: Dict[DonationTokenClaim, LnUrl] = {}
    _ids: Dict[DonationTokenClaim, int] = {}
    _status: Dict[DonationTokenClaim, List[str]] = {}

    def add(self, claim: DonationTokenClaim, id: int, ln_url: LnUrl) -> None:
        self._lnurls[claim] = ln_url
        self._ids[claim] = id
        self._status[claim] = [f"[{datetime().isoformat()}] Claim created, waiting for payment..."]

    def change_status(self, claim: DonationTokenClaim, status: str) -> None:
        self._status[claim].append(f"[{datetime().isoformat()}] {status}")

    def get_claim_by_id(self, id: int) -> Optional[DonationTokenClaim]:
        return dict_key_by_value(self._ids, id)
