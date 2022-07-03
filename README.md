# Donation Key Server

```
python3.10 -m venv venv
source venv/bin/activate
pip install asyncio aiohttp
# For development
pip install black mypy
```

Env:

```
LNURL_TOKEN="<lnurl-token>" SATS_AMOUNT="<required payment in sats>"
```

Check:

```
black --target-version py310 . && mypy --strict --show-error-codes src
```
