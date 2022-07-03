from typing import Dict, Optional, TypeVar


T = TypeVar("T")
K = TypeVar("K")


def dict_key_by_value(d: Dict[K, T], value: T) -> Optional[K]:
    return list(d.keys())[list(d.values()).index(value)]
