#!/usr/bin/env python3
"""Download a CIF or XAS reference file with basic validation and provenance."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request


def validate_cif(data: bytes) -> dict:
    text = data.decode("utf-8", errors="replace")
    checks = {
        "data_block": bool(re.search(r"(?mi)^data_\S+", text)),
        "cell_a": "_cell_length_a" in text,
        "cell_b": "_cell_length_b" in text,
        "cell_c": "_cell_length_c" in text,
        "atom_sites": "_atom_site_" in text,
    }
    if not all(checks.values()):
        missing = ", ".join(k for k, ok in checks.items() if not ok)
        raise ValueError(f"payload does not look like a structure CIF; missing {missing}")
    return checks


def validate_xas(data: bytes) -> dict:
    text = data.decode("utf-8", errors="replace")
    numeric_rows = 0
    max_columns = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";", "!")):
            continue
        parts = re.split(r"[\s,]+", line)
        try:
            [float(x) for x in parts[:2]]
        except (ValueError, IndexError):
            continue
        numeric_rows += 1
        max_columns = max(max_columns, len(parts))
    if numeric_rows < 10 or max_columns < 2:
        raise ValueError("payload does not contain at least 10 two-column numeric XAS rows")
    return {"numeric_rows": numeric_rows, "max_columns": max_columns}


def main() -> int:
    p = argparse.ArgumentParser()
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="Direct authorized download URL")
    src.add_argument("--cod-id", help="Numeric Crystallography Open Database ID")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--kind", choices=("auto", "cif", "xas"), default="auto")
    p.add_argument("--expected-sha256")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    url = args.url or f"https://www.crystallography.net/cod/{args.cod_id}.cif"
    kind = args.kind
    if kind == "auto":
        kind = "cif" if args.cod_id or url.lower().split("?")[0].endswith(".cif") else "xas"

    output = args.output.resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing file: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(url, headers={"User-Agent": "artemis-xafs-fit-skill/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
        final_url = response.geturl()
        content_type = response.headers.get("Content-Type", "")
    head = payload[:512].lower()
    if b"<html" in head or b"<!doctype html" in head:
        raise SystemExit("download returned HTML rather than the requested data file")

    digest = hashlib.sha256(payload).hexdigest()
    if args.expected_sha256 and digest.lower() != args.expected_sha256.lower():
        raise SystemExit(f"SHA256 mismatch: got {digest}")
    validation = validate_cif(payload) if kind == "cif" else validate_xas(payload)

    fd, tmp_name = tempfile.mkstemp(prefix=output.name + ".", suffix=".part", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
        os.replace(tmp_name, output)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)

    provenance = {
        "requested_url": url,
        "final_url": final_url,
        "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sha256": digest,
        "bytes": len(payload),
        "content_type": content_type,
        "kind": kind,
        "validation": validation,
    }
    sidecar = output.with_suffix(output.suffix + ".provenance.json")
    sidecar.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "provenance": str(sidecar), **provenance}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
