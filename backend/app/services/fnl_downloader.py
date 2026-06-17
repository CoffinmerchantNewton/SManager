from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..core.config import settings

logger = logging.getLogger(__name__)

FNL_NAME_RE = re.compile(r"^fnl_(\d{4})(\d{2})(\d{2})_(\d{2})_00\.grib2$")
VALID_HOURS = {"00", "06", "12", "18"}


def parse_fnl_filename(filename: str) -> tuple[str, str, str]:
    match = FNL_NAME_RE.match(filename)
    if not match:
        raise ValueError(f"invalid FNL filename: {filename}")
    yyyy, mm, dd, hour = match.group(1), match.group(2), match.group(3), match.group(4)
    if hour not in VALID_HOURS:
        raise ValueError(f"invalid FNL hour: {hour}")
    return f"{yyyy}{mm}{dd}", hour, filename


def build_gdex_url(filename: str, base_url: str | None = None) -> str:
    _, hour, _ = parse_fnl_filename(filename)
    match = FNL_NAME_RE.match(filename)
    assert match
    yyyy, mm, dd = match.group(1), match.group(2), match.group(3)
    root = (base_url or settings.FNL_GDEX_BASE_URL).rstrip("/")
    folder = f"{yyyy}/{yyyy}.{mm}"
    return f"{root}/{folder}/fnl_{yyyy}{mm}{dd}_{hour}_00.grib2"


def cache_path(filename: str) -> Path:
    path = Path(settings.LOCAL_FNL_CACHE_DIR) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def remote_content_length(url: str) -> int | None:
    try:
        request = Request(url, method="HEAD")
        with urlopen(request, timeout=30) as response:
            value = response.headers.get("Content-Length")
            return int(value) if value else None
    except (HTTPError, URLError, OSError, ValueError):
        return None


def is_download_complete(url: str, local_path: Path) -> bool:
    if not local_path.is_file():
        return False
    remote_size = remote_content_length(url)
    if remote_size is None:
        return local_validate(local_path)[0]
    return local_path.stat().st_size == remote_size


def local_validate(local_path: Path) -> tuple[bool, str, dict]:
    min_bytes = int(settings.FNL_MIN_MB * 1024 * 1024)
    checks: dict = {"exists": local_path.is_file()}
    if not checks["exists"]:
        return False, "file missing", checks
    size = local_path.stat().st_size
    checks["size_bytes"] = size
    checks["size_ok"] = size >= min_bytes
    try:
        with local_path.open("rb") as handle:
            checks["grib_header"] = handle.read(4) == b"GRIB"
    except OSError as exc:
        return False, str(exc), checks
    ok = bool(checks["size_ok"] and checks["grib_header"])
    message = "local ok" if ok else "local validation failed"
    return ok, message, checks


def download_file(url: str, dest: Path) -> tuple[bool, str, int]:
    chunk_size = settings.FNL_DOWNLOAD_CHUNK_SIZE
    max_retries = settings.FNL_DOWNLOAD_MAX_RETRIES
    retry_delay = settings.FNL_DOWNLOAD_RETRY_DELAY
    part_path = dest.with_suffix(dest.suffix + ".part")

    for attempt in range(1, max_retries + 1):
        downloaded = 0
        try:
            with urlopen(url, timeout=120) as response:
                with part_path.open("wb") as handle:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        handle.write(chunk)
                        downloaded += len(chunk)
            os.replace(part_path, dest)
            ok, message, _ = local_validate(dest)
            if ok:
                return True, message, dest.stat().st_size
            dest.unlink(missing_ok=True)
            return False, message, downloaded
        except (HTTPError, URLError, OSError) as exc:
            part_path.unlink(missing_ok=True)
            dest.unlink(missing_ok=True)
            logger.warning("FNL download failed (%s/%s): %s", attempt, max_retries, exc)
            if attempt >= max_retries:
                return False, str(exc), downloaded
            time.sleep(retry_delay)
    return False, "max retries exceeded", 0


def ensure_local_file(filename: str, *, use_cache: bool = True) -> tuple[bool, str, Path | None, dict]:
    url = build_gdex_url(filename)
    dest = cache_path(filename)
    meta = {"filename": filename, "url": url, "local_path": str(dest)}

    if use_cache and is_download_complete(url, dest):
        ok, message, checks = local_validate(dest)
        meta.update(checks)
        meta["source"] = "cache"
        return ok, message if ok else "cached file invalid", dest if ok else None, meta

    ok, message, size = download_file(url, dest)
    meta["source"] = "download"
    meta["size_bytes"] = size
    if not ok:
        return False, message, None, meta

    ok, message, checks = local_validate(dest)
    meta.update(checks)
    return ok, message, dest if ok else None, meta
