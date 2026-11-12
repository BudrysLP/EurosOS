"""Offline regression: stage only source matching a pinned GitHub Git tree."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "euros_stage9_staging", ROOT / "scripts" / "prepare_ha_stage9_candidate.py"
)
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)
SHA = "07a49bccc0cb590f3179983156c706dbe4675189"


def fixture_files():
    names = sorted(set(tool.REQUIRED) | {f"translations/demo_{i}.txt" for i in range(7)})
    assert len(names) == 15
    result = {name: f"example:{name}".encode() for name in names}
    result["manifest.json"] = b'{"domain":"euros_os","version":"0.1.0"}'
    return result


def git_blob_hash(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + bytes([0]) + data).hexdigest()


def fixture_sources(*, corrupt=False, extra=False, symlink=False):
    files = fixture_files()
    tree = {"truncated": False, "tree": [
        {"path": tool.PREFIX + name, "sha": git_blob_hash(data), "type": "blob"}
        for name, data in files.items()
    ]}
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        for name, data in files.items():
            if corrupt and name == "sensor.py":
                data = b"wrong data"
            info = tarfile.TarInfo(
                "BudrysLP-EurosOS-test/" + tool.PREFIX + name
            )
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        if extra:
            data = b"wrong extra"
            name = "BudrysLP-EurosOS-test/" + tool.PREFIX + "bad.py"
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        if symlink:
            info = tarfile.TarInfo(
                "BudrysLP-EurosOS-test/" + tool.PREFIX + "danger.txt"
            )
            info.type = tarfile.SYMTYPE
            info.linkname = "../../../../etc/passwd"
            tar.addfile(info)
    tree_data = json.dumps(tree).encode()
    archive_data = archive.getvalue()
    return (lambda url, max_size:
            tree_data if "/git/trees/" in url else archive_data)


class Stage9StagingTests(unittest.TestCase):
    def setUp(self):
        context = tempfile.TemporaryDirectory()
        self.addCleanup(context.cleanup)
        self.folder = Path(context.name) / "private"

    def test_stage_exactly_fifteen_verified_files_without_touching_live(self):
        path, count = tool.stage(SHA, self.folder, fetch=fixture_sources())
        self.assertEqual(count, 15)
        self.assertEqual(path.name, "stage9_candidate_" + SHA[:12])
        self.assertEqual(
            (path / "euros_os" / "manifest.json").read_bytes(),
            b'{"domain":"euros_os","version":"0.1.0"}'
        )
        self.assertEqual(
            json.loads((path / "source-verification.json").read_text())["source_commit"], SHA
        )
        self.assertEqual(
            len([p for p in (path / "euros_os").rglob("*") if p.is_file()]), 15
        )

    def test_corrupted_tarball_is_rejected_and_leaves_no_stage(self):
        with self.assertRaisesRegex(ValueError, "blob verification failed"):
            tool.stage(SHA, self.folder, fetch=fixture_sources(corrupt=True))
        self.assertFalse(self.folder.exists())

    def test_unexpected_member_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected source file"):
            tool.stage(SHA, self.folder, fetch=fixture_sources(extra=True))
        self.assertFalse(self.folder.exists())

    def test_symlink_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Non-regular file"):
            tool.stage(SHA, self.folder, fetch=fixture_sources(symlink=True))
        self.assertFalse(self.folder.exists())

    def test_candidate_is_never_overwritten(self):
        tool.stage(SHA, self.folder, fetch=fixture_sources())
        with self.assertRaises(FileExistsError):
            tool.stage(SHA, self.folder, fetch=fixture_sources())

    def test_truncated_tree_is_rejected(self):
        bad_tree = json.dumps({"truncated": True, "tree": []}).encode()
        fetch = lambda url, max_size: bad_tree
        with self.assertRaisesRegex(ValueError, "Incomplete GitHub"):
            tool.stage(SHA, self.folder, fetch=fetch)
        self.assertFalse(self.folder.exists())

    def test_invalid_commit_is_rejected_without_network(self):
        with self.assertRaisesRegex(ValueError, "full lowercase"):
            tool.stage("main", self.folder, fetch=fixture_sources())
        self.assertFalse(self.folder.exists())


if __name__ == "__main__":
    unittest.main()
