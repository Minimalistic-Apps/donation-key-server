# Donation Key Server

```
python3.10 -m venv venv
source venv/bin/activate
pip install asyncio aiohttp pydantic rsa

# For development
pip install black mypy pytest
```

Env:

```
PRIVATE_KEY="" DOMAIN="" LN_BITS_API_KEY="" LN_BITS_URL="" SATS_AMOUNT=""
```

Check:

```
black --target-version py310 . && mypy --strict --show-error-codes src
```

Test:

```
python -m pytest -vv
```
