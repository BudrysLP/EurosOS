"""Verify and stage a pinned Euros OS GitHub commit outside live Home Assistant.

Read-only with respect to /config/custom_components/euros_os, HA registries,
services and MQTT. It creates a new private staging directory only after
checking all integration files against their Git *blob* hashes.

Example (after reviewing the script and exact SHA):
    python3 prepare_ha_stage9_candidate.py \
      --sha 07a49bccc0cb590f3179983156c706dbe4675189 \
      --stage-root /config/euros_os_stage9_private

Result: stage9_candidate_<sha-prefix>/euros_os/ with 15 verified runtime files.
This does NOT install an integration, restart HA or publish a GitHub Release.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile
from urllib.request import Request, urlopen

REPO = "BudrysLP/EurosOS"
PREFIX = "custom_components/euros_os/"
MARKER = "/" + PREFIX
REQUIRED = frozenset({
    "__init__.py", "coordinator.py", "sensor.py", "config_flow.py",
    "manifest.json", "const.py", "ems.py", "geo.py",
})
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_TREE_BYTES = 2 * 1024 * 1024


def fetch_public_bytes(url: str, max_size: int) -> bytes:
    req = Request(url, headers={"User-Agent": "euros-os-stage9-verify/1"})
    with urlopen(req, timeout=35) as response:
        data = response.read(max_size + 1)
    if len(data) > max_size:
        raise ValueError("Unexpectedly large GitHub response")
    return data


def expected_blobs(commit: str, tree_json: bytes) -> dict[str, str]:
    result = json.loads(tree_json)
    if result.get("truncated"):
        raise ValueError("Incomplete GitHub repository tree")
    if not isinstance(result.get("tree"), list):
        raise ValueError("GitHub did not provide a valid repository tree")
    found = {}
    for node in result["tree"]:
        name = node.get("path", "")
        if not isinstance(name, str) or not name.startswith(PREFIX):
            continue
        if node.get("type") != "blob":
            continue
        relative = name[len(PREFIX):]
        parts = PurePosixPath(relative).parts
        if not relative or ".." in parts or relative.startswith("/"):
            raise ValueError("Unsafe path in git tree")
        blob = node.get("sha")
        if not isinstance(blob, str) or not re.fullmatch(r"[a-f0-9]{40}", blob):
            raise ValueError(f"Invalid blob SHA for {relative}")
        if relative in found:
            raise ValueError("Duplicate Git tree path")
        found[relative] = blob
    if not REQUIRED.issubset(found) or len(found) != 15:
        raise ValueError(f"Unexpected integration tree (got {len(found)} files)")
    return found


def extract_verified_files(archive: bytes, blobs: dict[str, str]) -> dict[str, bytes]:
    actual = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
        for member in tf:
            if MARKER not in member.name:
                continue
            name = member.name.split(MARKER, 1)[1]
            if not name:
                continue
            parts = PurePosixPath(name).parts
            if name.startswith("/") or ".." in parts or "\\" in name:
                raise ValueError(f"Unsafe file path in archive: {name!r}")
            if member.isdir():
                continue
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError(f"Non-regular file in integration: {name}")
            if name in actual:
                raise ValueError(f"Duplicate archive file: {name}")
            if name not in blobs:
                raise ValueError(f"Unexpected source file in archive: {name}")
            stream = tf.extractfile(member)
            if stream is None:
                raise ValueError(f"Unreadable tar member: {name}")
            data = stream.read()
            calculated_sha = hashlib.sha1(
                b"blob " + str(len(data)).encode("ascii") + bytes([0]) + data
            ).hexdigest()
            if calculated_sha != blobs[name]:
                raise ValueError(f"Git blob verification failed for {name}")
            actual[name] = data
    if actual.keys() != blobs.keys():
        missing = sorted(blobs.keys() - actual.keys())
        raise ValueError(f"Archive is missing integration files: {missing}")
    manifest = json.loads(actual["manifest.json"])
    if manifest.get("domain") != "euros_os":
        raise ValueError("Wrong integration domain")
    return actual


def stage(commit: str, output_root: Path, *,
          fetch=fetch_public_bytes) -> tuple[Path, int]:
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Commit must be a full lowercase 40-character SHA")
    output_root = output_root.resolve()
    live_root = Path("/config/custom_components").resolve()
    if output_root == live_root or live_root in output_root.parents:
        raise ValueError("Refusing to stage inside the live integration directory")
    dest = output_root / f"stage9_candidate_{commit[:12]}"
    if dest.exists():
        raise FileExistsError("Candidate staging directory already exists; will not overwrite")

    base = f"https://api.github.com/repos/{REPO}"
    tree = fetch(f"{base}/git/trees/{commit}?recursive=1", MAX_TREE_BYTES)
    blobs = expected_blobs(commit, tree)
    source = fetch(f"{base}/tarball/{commit}", MAX_ARCHIVE_BYTES)
    files = extract_verified_files(source, blobs)

    output_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix=".stage9_tmp_", dir=output_root) as temp:
        tmpdir = Path(temp)
        folder = tmpdir / "euros_os"
        folder.mkdir(mode=0o700)
        for rel, data in sorted(files.items()):
            path = folder.joinpath(*PurePosixPath(rel).parts)
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with path.open("xb") as stream:
                stream.write(data)
            os.chmod(path, 0o600)
        evidence = {
            "source_commit": commit,
            "source_repository": REPO,
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "runtime_file_count": len(files),
            "git_blob_validation": "all matched",
            "scope": "STAGING ONLY; live integration unchanged",
        }
        (tmpdir / "source-verification.json").write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
        )
        tmpdir.rename(dest)
    return dest, len(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--stage-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        dest, count = stage(args.sha, args.stage_root)
    except (ValueError, OSError, json.JSONDecodeError, tarfile.TarError) as exc:
        print(f"STOP: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"STAGED ONLY: {count}/15 verified integration files")
    print(f"COMMIT: {args.sha}")
    print(f"STAGING DIRECTORY: {dest}/euros_os")
    print("LIVE INTEGRATION: UNCHANGED; NO HA RESTART")
    return 0


if __name__ == "__main__":
    sys.exit(main())
