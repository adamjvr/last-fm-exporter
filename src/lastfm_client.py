from __future__ import annotations

"""
lastfm_client.py

This module contains a small, object-oriented client wrapper around the
Last.fm REST API. The goal is to keep all network and API-related logic
in one place so the rest of the code (exporter, GUI) can treat it as a
simple, high-level service.

Classes:
    LastFMError   -- Custom exception type for Last.fm-related problems.
    LastFMClient  -- Main client for fetching a user's library data.

Typical usage:

    from lastfm_client import LastFMClient, LastFMError

    client = LastFMClient(api_key="YOUR_KEY_HERE")
    artists = client.get_user_artists("username")
    albums = client.get_user_albums("username")
"""

import requests
from typing import Any, Dict, Generator, List, Optional

# Base URL for the Last.fm API.
API_ROOT = "http://ws.audioscrobbler.com/2.0/"

# Default network timeout (seconds) for each HTTP request.
DEFAULT_TIMEOUT = 15.0


class LastFMError(Exception):
    """
    Custom exception type for all Last.fm-related issues.

    This allows us to catch Last.fm-specific errors (network failures,
    invalid responses, API error codes, etc.) separately from generic
    Python exceptions.
    """
    pass


class LastFMClient:
    """
    High-level client for interacting with the Last.fm REST API.

    Responsibilities:
    - Handle HTTP requests and basic error checking.
    - Add required query parameters (API key, format).
    - Provide convenient methods for fetching:
        * All artists in a user's library (with playcounts & metadata).
        * All albums in a user's library (with playcounts & metadata).
    - Provide a generic pagination helper usable for other endpoints later.

    The design intentionally keeps this class **stateless** except for
    the API key and timeout, so it can be safely reused across the app.
    """

    def __init__(self, api_key: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        """
        Initialize a new LastFMClient.

        Parameters
        ----------
        api_key : str
            Your Last.fm API key. This is NOT the user's password; it is
            a public API credential obtained from Last.fm's developer site.
        timeout : float, optional
            Network timeout (per request) in seconds. Defaults to DEFAULT_TIMEOUT.
        """
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method_name: str, **params: Any) -> Dict[str, Any]:
        """
        Perform a single GET request to the Last.fm API.
        """
        query = {
            "method": method_name,
            "api_key": self.api_key,
            "format": "json",
        }
        query.update(params)

        try:
            response = requests.get(
                API_ROOT,
                params=query,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise LastFMError(f"Network error calling Last.fm: {exc}") from exc

        if not response.ok:
            raise LastFMError(
                f"HTTP error from Last.fm: {response.status_code} {response.reason}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LastFMError("Failed to decode JSON from Last.fm response") from exc

        if isinstance(data, dict) and "error" in data:
            code = data.get("error")
            message = data.get("message", "Unknown Last.fm error")
            raise LastFMError(f"Last.fm API error {code}: {message}")

        return data

    def _iter_paginated(
        self,
        *,
        method_name: str,
        user: str,
        root_key: str,
        list_key: str,
        limit_per_page: int = 1000,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Generic pagination helper for endpoints that return paginated data.
        """
        if extra_params is None:
            extra_params = {}

        current_page = 1
        total_pages: Optional[int] = None

        while True:
            params = {
                "user": user,
                "limit": limit_per_page,
                "page": current_page,
            }
            params.update(extra_params)

            data = self._request(method_name, **params)

            container = data.get(root_key)
            if container is None:
                raise LastFMError(
                    f"Unexpected response: key '{root_key}' missing "
                    f"for method {method_name}"
                )

            items = container.get(list_key, [])
            if isinstance(items, dict):
                items = [items]

            for item in items:
                yield item

            if total_pages is None:
                attr = container.get("@attr", {})
                total_pages_str = attr.get("totalPages") or attr.get("totalpages")
                if total_pages_str is not None:
                    try:
                        total_pages = int(total_pages_str)
                    except (TypeError, ValueError):
                        total_pages = 1
                else:
                    total_pages = 1

            if current_page >= total_pages:
                break

            current_page += 1

    def get_user_artists(
        self,
        user: str,
        limit_per_page: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch ALL artists in a user's library.
        """
        artists: List[Dict[str, Any]] = []

        for artist in self._iter_paginated(
            method_name="library.getartists",
            user=user,
            root_key="artists",
            list_key="artist",
            limit_per_page=limit_per_page,
        ):
            artists.append(artist)

        return artists

    def get_user_albums(
        self,
        user: str,
        limit_per_page: int = 1000,
        artist_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch ALL albums in a user's library.
        """
        extra_params: Dict[str, Any] = {}
        if artist_filter:
            extra_params["artist"] = artist_filter

        albums: List[Dict[str, Any]] = []

        for album in self._iter_paginated(
            method_name="library.getalbums",
            user=user,
            root_key="albums",
            list_key="album",
            limit_per_page=limit_per_page,
            extra_params=extra_params,
        ):
            albums.append(album)

        return albums
