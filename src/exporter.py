from __future__ import annotations

"""
exporter.py

High-level "export manager" that:
- Uses a LastFMClient to fetch a user's artists and albums.
- Exposes simple methods for exporting that data to JSON and/or CSV.
"""

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from lastfm_client import LastFMClient


@dataclass
class ExportResult:
    artists_count: int
    albums_count: int
    json_path: Optional[Path]
    artists_csv_path: Optional[Path]
    albums_csv_path: Optional[Path]


class LastFMLibraryExporter:
    def __init__(self, client: LastFMClient, username: str) -> None:
        self.client = client
        self.username = username

    def export_library(
        self,
        *,
        output_dir: Path,
        base_name: str = "lastfm_export",
        write_json: bool = True,
        write_csv: bool = True,
        artists_per_page: int = 1000,
        albums_per_page: int = 1000,
    ) -> ExportResult:
        output_dir.mkdir(parents=True, exist_ok=True)

        artists = self.client.get_user_artists(
            self.username,
            limit_per_page=artists_per_page,
        )

        albums = self.client.get_user_albums(
            self.username,
            limit_per_page=albums_per_page,
        )

        export_payload: Dict[str, Any] = {
            "user": self.username,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "artists": artists,
            "albums": albums,
        }

        json_path: Optional[Path] = None
        artists_csv_path: Optional[Path] = None
        albums_csv_path: Optional[Path] = None

        if write_json:
            json_path = output_dir / f"{base_name}.json"
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(export_payload, f, ensure_ascii=False, indent=2)

        if write_csv:
            artists_csv_path = output_dir / f"{base_name}_artists.csv"
            albums_csv_path = output_dir / f"{base_name}_albums.csv"
            self._write_artists_csv(artists, artists_csv_path)
            self._write_albums_csv(albums, albums_csv_path)

        return ExportResult(
            artists_count=len(artists),
            albums_count=len(albums),
            json_path=json_path,
            artists_csv_path=artists_csv_path,
            albums_csv_path=albums_csv_path,
        )

    def _write_artists_csv(
        self,
        artists: List[Dict[str, Any]],
        csv_path: Path,
    ) -> None:
        fieldnames = [
            "name",
            "mbid",
            "playcount",
            "url",
            "streamable",
            "tagcount",
        ]

        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for artist in artists:
                row = {
                    "name": artist.get("name", ""),
                    "mbid": artist.get("mbid", ""),
                    "playcount": artist.get("playcount", ""),
                    "url": artist.get("url", ""),
                    "streamable": artist.get("streamable", ""),
                    "tagcount": artist.get("tagcount", ""),
                }
                writer.writerow(row)

    def _write_albums_csv(
        self,
        albums: List[Dict[str, Any]],
        csv_path: Path,
    ) -> None:
        fieldnames = [
            "name",
            "artist",
            "mbid",
            "playcount",
            "url",
        ]

        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for album in albums:
                row = {
                    "name": album.get("name", ""),
                    "artist": self._extract_album_artist(album),
                    "mbid": album.get("mbid", ""),
                    "playcount": album.get("playcount", ""),
                    "url": album.get("url", ""),
                }
                writer.writerow(row)

    @staticmethod
    def _extract_album_artist(album: Dict[str, Any]) -> str:
        artist_value = album.get("artist", "")

        if isinstance(artist_value, dict):
            return artist_value.get("name", "")

        if isinstance(artist_value, str):
            return artist_value

        return ""
