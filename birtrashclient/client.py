"""Client library for the BIR Trash Collection API."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

TRANSIENT_STATUS_CODES = {500, 502, 503, 504}
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 2.0


class BirTrashAuthError(Exception):
    """Exception raised when authentication fails."""


class BirTrashConnectionError(Exception):
    """Exception raised when a connection error occurs."""


class BirTrashClient:
    """Async client for the BIR Trash Collection API."""

    def __init__(
        self,
        app_id: str,
        contractor_id: str,
        request_timeout: int = 10,
        session: aiohttp.ClientSession | None = None,
        retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF,
    ) -> None:
        """Initialize the client.

        Args:
            app_id: The application ID for API authentication.
            contractor_id: The contractor ID for API authentication.
            request_timeout: Timeout in seconds for HTTP requests.
            session: An optional aiohttp ClientSession to reuse.
            retries: Number of retries for transient server errors.
            backoff_factor: Base delay multiplier for exponential backoff.
        """
        self.base_url = "https://webservice.bir.no/api"
        self.request_timeout = aiohttp.ClientTimeout(total=request_timeout)
        self.app_id = app_id
        self.contractor_id = contractor_id
        self.token: str | None = None
        self._session = session
        self._close_session = False
        self.retries = retries
        self.backoff_factor = backoff_factor

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return the active session, creating one if needed."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._close_session = True
        return self._session

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        """Execute an HTTP request with retry logic for transient errors.

        Args:
            method: The HTTP method (get, post, etc.).
            url: The full URL to request.
            **kwargs: Additional arguments passed to the aiohttp request.

        Returns:
            The parsed JSON response.

        Raises:
            BirTrashAuthError: On 401 after re-authentication also fails.
            BirTrashConnectionError: After all retries are exhausted.
        """
        session = await self._get_session()
        last_exception: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                async with session.request(
                    method,
                    url,
                    timeout=self.request_timeout,
                    **kwargs,
                ) as response:
                    if response.status == 401:
                        _LOGGER.debug(
                            "Token expired (attempt %d), re-authenticating",
                            attempt + 1,
                        )
                        await self.authenticate()
                        if "headers" in kwargs and kwargs["headers"]:
                            kwargs["headers"]["Token"] = self.token
                        continue

                    if response.status in TRANSIENT_STATUS_CODES:
                        delay = self.backoff_factor * (2 ** attempt)
                        _LOGGER.warning(
                            "Server returned %d (attempt %d/%d), "
                            "retrying in %.1f s",
                            response.status,
                            attempt + 1,
                            self.retries + 1,
                            delay,
                        )
                        last_exception = BirTrashConnectionError(
                            f"Server returned {response.status}"
                        )
                        await asyncio.sleep(delay)
                        continue

                    response.raise_for_status()
                    return await response.json()

            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                delay = self.backoff_factor * (2 ** attempt)
                _LOGGER.warning(
                    "Request failed (attempt %d/%d): %s, retrying in %.1f s",
                    attempt + 1,
                    self.retries + 1,
                    err,
                    delay,
                )
                last_exception = err
                if attempt < self.retries:
                    await asyncio.sleep(delay)

        raise BirTrashConnectionError(
            f"Request failed after {self.retries + 1} attempts"
        ) from last_exception

    async def authenticate(self) -> None:
        """Authenticate with the BIR API and store the token.

        Raises:
            BirTrashAuthError: If the authentication request fails.
        """
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.base_url}/login",
                json={
                    "applikasjonsId": self.app_id,
                    "oppdragsgiverId": self.contractor_id,
                },
                timeout=self.request_timeout,
            ) as response:
                response.raise_for_status()
                self.token = response.headers["Token"]
        except KeyError as err:
            raise BirTrashAuthError(
                "Authentication succeeded but response contained no Token header"
            ) from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise BirTrashAuthError(
                f"Authentication failed: {err}"
            ) from err

    @staticmethod
    def _normalize_address(address: str) -> str:
        """Insert a space between street number and unit letter if missing.

        Converts e.g. '46J' -> '46 J' to match the API's expected format.
        """
        return re.sub(r"(\d)([A-Za-z])$", r"\1 \2", address.strip())

    async def search_addresses(self, address: str) -> list[dict[str, Any]]:
        """Search for an address and return all matching properties.

        Useful for Home Assistant config flows where the user selects
        from a list of matching properties (e.g. multiple units at one
        street number).

        Args:
            address: The street address to search for.

        Returns:
            A list of property dicts, each containing at minimum 'id'
            and 'adresse' keys.

        Raises:
            BirTrashConnectionError: If the request fails after retries.
        """
        return await self._request_with_retry(
            "get",
            f"{self.base_url}/eiendommer",
            params={"adresse": self._normalize_address(address)},
            headers={"Token": self.token},
        )

    async def search_address(self, address: str) -> str | None:
        """Search for an address and return the corresponding property ID.

        The address is normalized before searching — a space is inserted
        between the street number and unit letter if missing
        (e.g. '46J' becomes '46 J').

        Args:
            address: The street address to search for.

        Returns:
            The property ID string for the first matching property, or None
            if the result contains no id.

        Raises:
            BirTrashConnectionError: If the request fails after retries.
        """
        result = await self.search_addresses(address)
        return result[0].get("id")

    async def get_calendar(
        self, address_id: str, from_date: str, to_date: str
    ) -> list[dict[str, Any]]:
        """Get the pickup calendar for the provided address ID.

        Args:
            address_id: The property ID to query.
            from_date: The start date in YYYY-MM-DD format.
            to_date: The end date in YYYY-MM-DD format.

        Returns:
            A list of pickup schedule dictionaries.

        Raises:
            BirTrashConnectionError: If the request fails after retries.
        """
        return await self._request_with_retry(
            "get",
            f"{self.base_url}/tomminger",
            params={
                "datoFra": from_date,
                "datoTil": to_date,
                "eiendomId": address_id,
            },
            headers={"Token": self.token},
        )

    async def close(self) -> None:
        """Close the underlying session if we own it."""
        if self._session and self._close_session:
            await self._session.close()
