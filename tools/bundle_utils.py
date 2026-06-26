from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class BundleEntry:
    asset_type: str
    asset_key: str
    size: int
    sha256: str
    data_offset: int


def read_u32(handle) -> int:
    raw = handle.read(4)
    if len(raw) != 4:
        raise EOFError("unexpected end of bundle while reading u32")
    return struct.unpack("<I", raw)[0]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_bundle_entries(bundle_path: Path) -> Iterator[BundleEntry]:
    with bundle_path.open("rb") as handle:
        entry_count = read_u32(handle)
        for _index in range(entry_count):
            type_len = read_u32(handle)
            asset_type = handle.read(type_len).decode("utf-8", "replace")
            key_len = read_u32(handle)
            asset_key = handle.read(key_len).decode("utf-8", "replace")
            data_len = read_u32(handle)
            data_offset = handle.tell()
            digest = hashlib.sha256()
            remaining = data_len
            while remaining:
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise EOFError(f"unexpected end of bundle while reading asset data for {asset_key}")
                digest.update(chunk)
                remaining -= len(chunk)
            yield BundleEntry(
                asset_type=asset_type,
                asset_key=asset_key,
                size=data_len,
                sha256=digest.hexdigest(),
                data_offset=data_offset,
            )


def read_bundle_entry(bundle_path: Path, key: str) -> tuple[str, bytes]:
    with bundle_path.open("rb") as handle:
        entry_count = read_u32(handle)
        for _index in range(entry_count):
            type_len = read_u32(handle)
            asset_type = handle.read(type_len).decode("utf-8", "replace")
            key_len = read_u32(handle)
            asset_key = handle.read(key_len).decode("utf-8", "replace")
            data_len = read_u32(handle)
            data = handle.read(data_len)
            if len(data) != data_len:
                raise EOFError(f"unexpected end of bundle while reading asset data for {asset_key}")
            if asset_key == key:
                return asset_type, data
    raise KeyError(f"asset key not found in bundle: {key}")


def write_synthetic_bundle(path: Path, entries: list[tuple[str, str, bytes]]) -> None:
    out = bytearray()
    out += len(entries).to_bytes(4, "little")
    for asset_type, asset_key, payload in entries:
        type_bytes = asset_type.encode("utf-8")
        key_bytes = asset_key.encode("utf-8")
        out += len(type_bytes).to_bytes(4, "little")
        out += type_bytes
        out += len(key_bytes).to_bytes(4, "little")
        out += key_bytes
        out += len(payload).to_bytes(4, "little")
        out += payload
    path.write_bytes(bytes(out))
