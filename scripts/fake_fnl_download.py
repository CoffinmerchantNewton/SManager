#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


DEFAULT_SIZE_MB = 6


def main() -> int:
    output_path = require_env("FNL_OUTPUT_PATH")
    valid_time = os.environ.get("FNL_VALID_TIME", "unknown")
    file_name = os.environ.get("FNL_FILE_NAME", Path(output_path).name)
    size_mb = int(os.environ.get("FNL_FAKE_SIZE_MB", str(DEFAULT_SIZE_MB)))
    if size_mb <= 0:
        raise ValueError("FNL_FAKE_SIZE_MB must be positive")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    target_size = size_mb * 1024 * 1024
    header = f"GRIB fake FNL {valid_time} {file_name}\n".encode("ascii", errors="ignore")
    with path.open("wb") as handle:
        handle.write(header)
        remaining = target_size - len(header)
        if remaining > 0:
            handle.write(b"\0" * remaining)
    print(f"wrote fake FNL {path} ({target_size} bytes)")
    return 0


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
