"""Integration test against the real BIR API.

Usage:
    BIR_APP_ID=xxx BIR_CONTRACTOR_ID=yyy BIR_ADDRESS="Storgata 1" python test_integration.py
"""

import asyncio
import os
from datetime import date, timedelta

from birtrashclient import BirTrashAuthError, BirTrashClient, BirTrashConnectionError


async def main() -> None:
    app_id = os.environ.get("BIR_APP_ID")
    contractor_id = os.environ.get("BIR_CONTRACTOR_ID")
    address = os.environ.get("BIR_ADDRESS")

    if not app_id or not contractor_id or not address:
        raise SystemExit(
            "Set BIR_APP_ID, BIR_CONTRACTOR_ID, and BIR_ADDRESS environment variables."
        )

    client = BirTrashClient(app_id=app_id, contractor_id=contractor_id)

    try:
        print("Authenticating...")
        await client.authenticate()
        print(f"  Token: {client.token[:20]}...")

        print(f"\nSearching for address: {address!r}")
        address_id = await client.search_address(address)
        print(f"  Property ID: {address_id}")

        from_date = date.today().isoformat()
        to_date = (date.today() + timedelta(days=90)).isoformat()
        print(f"\nFetching calendar ({from_date} -> {to_date})...")
        calendar = await client.get_calendar(address_id, from_date, to_date)
        print(f"  {len(calendar)} pickup(s) found:")
        for entry in calendar:
            print(f"    {entry}")

    except BirTrashAuthError as err:
        print(f"Auth error: {err}")
        raise SystemExit(1)
    except BirTrashConnectionError as err:
        print(f"Connection error: {err}")
        raise SystemExit(1)
    finally:
        await client.close()


asyncio.run(main())
