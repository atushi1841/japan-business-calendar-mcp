#!/usr/bin/env python3
"""Pack japan-business-calendar-mcp into server.mcpb (zip bundle for MCP registry).

Mirrors the jepx packer: zip the repo minus .mcpbignore patterns, compute
sha256, and rewrite server.json with the release URL + fileSha256.

Usage:
  python3 scripts/pack_mcpb.py            # local bundle only
  python3 scripts/pack_mcpb.py --upload   # bundle + gh release upload + rewrite server.json
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IGNORE = set()
p = ROOT / ".mcpbignore"
if p.exists():
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            IGNORE.add(line)

EXTRA_IGNORE = {".git", ".github", "__pycache__", ".pytest_cache", ".mypy_cache",
                ".ruff_cache", "scripts", "tests", "server.mcpb", "uv.lock",
                ".actor", "smoke_rest.py", "verify_jepx.py", "pay_per_event.json"}


def _ignored(rel: str) -> bool:
    parts = rel.split("/")
    if parts[0] in EXTRA_IGNORE or parts[0] in IGNORE:
        return True
    for pat in IGNORE:
        if pat.endswith("/") and rel.startswith(pat):
            return True
        if pat == rel:
            return True
    return False


def pack() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if _ignored(rel):
                continue
            z.write(path, rel)
    return buf.getvalue()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--version", default="0.1.0")
    args = ap.parse_args()

    data = pack()
    out = ROOT / "server.mcpb"
    out.write_bytes(data)
    digest = sha256(data)
    print(f"PACKED {out} {len(data)} bytes sha256={digest}")

    if args.upload:
        tag = f"v{args.version}"
        subprocess.run(["gh", "release", "upload", tag, str(out), "--clobber"],
                       cwd=str(ROOT), check=True)
        url = (f"https://github.com/atushi1841/japan-business-calendar-mcp/"
               f"releases/download/{tag}/server.mcpb")
        sj = ROOT / "server.json"
        s = json.loads(sj.read_text(encoding="utf-8"))
        s["packages"][0]["identifier"] = url
        s["packages"][0]["version"] = args.version
        s["packages"][0]["fileSha256"] = digest
        s["version"] = args.version
        sj.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        print("SERVER_JSON", url)
        # also commit
        subprocess.run(["git", "add", "server.json", "server.mcpb", "manifest.json"],
                       cwd=str(ROOT), check=True)
        subprocess.run(["git", "commit", "-m",
                        f"publish japan-business-calendar-mcp {args.version} (mcpb + server.json)"],
                       cwd=str(ROOT), check=True)
        subprocess.run(["git", "push"], cwd=str(ROOT), check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())