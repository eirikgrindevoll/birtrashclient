# birtrashclient

Async Python client for the [BIR](https://bir.no) Trash Collection API.

## Installation

```bash
pip install birtrashclient
```

## Usage

```python
import asyncio
from birtrashclient import BirTrashClient

async def main():
    client = BirTrashClient(app_id="your_app_id", contractor_id="your_contractor_id")
    await client.authenticate()

    address_id = await client.search_address("Storgata 1, Bergen")
    calendar = await client.get_calendar(address_id, "2024-01-01", "2024-12-31")

    for entry in calendar:
        print(entry)

    await client.close()

asyncio.run(main())
```

## API

### `BirTrashClient(app_id, contractor_id, ...)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `app_id` | `str` | required | Application ID for API authentication |
| `contractor_id` | `str` | required | Contractor ID for API authentication |
| `request_timeout` | `int` | `10` | HTTP timeout in seconds |
| `session` | `aiohttp.ClientSession` | `None` | Optional session to reuse |
| `retries` | `int` | `3` | Retries on transient server errors |
| `backoff_factor` | `float` | `2.0` | Exponential backoff base multiplier |

### Methods

- `authenticate()` — Fetch and store an auth token
- `search_address(address)` — Resolve a street address to a property ID
- `get_calendar(address_id, from_date, to_date)` — Get pickup schedule (dates as `YYYY-MM-DD`)
- `close()` — Close the underlying HTTP session

## Exceptions

- `BirTrashAuthError` — Authentication failure
- `BirTrashConnectionError` — Connection or HTTP error after retries

## License

MIT
