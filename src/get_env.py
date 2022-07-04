import os


def get_env(name: str) -> str:
    raw = os.environ.get(name)
    if raw is None:
        raise Exception("ENV variable '" + name + "' is missing")

    return raw
