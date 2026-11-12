"""Test stage 9.5 preflight registry inspection without a Home Assistant host."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "stage9_private_snapshot", ROOT / "scripts" / "ha_registry_snapshot.py"
)
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def write_storage(config: Path, *, count=73, devices=2):
    storage = config / ".storage"
    storage.mkdir(parents=True)
    external_entry = {"entry_id": "other-id", "domain": "unrelated",
                      "data": {"token": "DO_NOT_EXPORT_ME"}}
    entries = [
        {"entry_id": "euros-entry", "domain": "euros_os",
         "data": {"password": "DO_NOT_EXPORT_ME"}},
        external_entry,
    ]
    rows = []
    for index in range(count):
        domain = "sensor" if index < 50 else "number"
        rows.append({
            "domain": domain,
            "platform": "euros_os",
            "unique_id": f"model_{index % 69}",
            "entity_id": f"{domain}.euros_os_fixture_{index}",
            "device_id": "pump-id" if index < 38 else "meter-id",
            "config_entry_id": "euros-entry",
            "attributes": {"private": "DO_NOT_EXPORT_ME"},
        })
    rows.append({
        "domain": "sensor", "platform": "another_integration",
        "unique_id": "foreign", "entity_id": "sensor.other",
        "config_entry_id": "other-id", "device_id": None,
    })
    device_records = [{
        "id": "pump-id", "via_device_id": None,
        "config_entries": ["euros-entry"], "identifiers": [["euros_os", "private"]]
    }]
    if devices == 2:
        device_records.append({
            "id": "meter-id", "via_device_id": "pump-id",
            "config_entries": ["euros-entry"], "name": "private friendly name",
        })
    for filename, field, records in (
        ("core.config_entries", "entries", entries),
        ("core.entity_registry", "entities", rows),
        ("core.device_registry", "devices", device_records),
    ):
        (storage / filename).write_text(
            json.dumps({"version": 1, "data": {field: records}}),
            encoding="utf-8",
        )


class Stage9RegistrySafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = Path(self.directory.name) / "ha-config"
        write_storage(self.config)

    def test_capture_exact_73_entities_and_two_devices_without_secrets(self):
        result = tool.capture(self.config)
        self.assertEqual(len(result["entities"]), 73)
        self.assertEqual(len(result["devices"]), 2)
        self.assertEqual(result["entry_count"], 1)
        self.assertNotIn("DO_NOT_EXPORT_ME", json.dumps(result))
        self.assertNotIn("password", json.dumps(result))
        self.assertNotIn("foreign", json.dumps(result))
        self.assertEqual(
            len({(e["domain"], e["platform"], e["unique_id"])
                 for e in result["entities"]}), 73
        )

    def test_compare_same_snapshot_passes(self):
        before = tool.capture(self.config)
        after = copy.deepcopy(before)
        after["captured_at_utc"] = "later"
        change = tool.differences(before, after)
        self.assertEqual(change["changed_entity_ids"], 0)
        self.assertEqual(change["changed_device_links"], 0)
        self.assertEqual(change["missing_entities"], 0)
        self.assertEqual(change["missing_devices"], 0)

    def test_changed_identity_is_detected(self):
        before = tool.capture(self.config)
        after = copy.deepcopy(before)
        after["entities"][0]["entity_id"] = "sensor.a_2"
        after["entities"][1]["device_id"] = "another"
        result = tool.differences(before, after)
        self.assertEqual(result["changed_entity_ids"], 1)
        self.assertEqual(result["changed_device_links"], 1)

    def test_missing_and_new_entities_are_detected(self):
        before = tool.capture(self.config)
        after = copy.deepcopy(before)
        after["entities"].pop()
        after["entities"].append({
            "domain": "sensor", "platform": "euros_os", "unique_id": "new",
            "entity_id": "sensor.new", "device_id": "pump-id"
        })
        result = tool.differences(before, after)
        self.assertEqual(result["missing_entities"], 1)
        self.assertEqual(result["new_entities"], 1)

    def test_change_to_meter_parent_link_is_detected(self):
        before = tool.capture(self.config)
        after = copy.deepcopy(before)
        next(d for d in after["devices"] if d["id"] == "meter-id")[
            "via_device_id"
        ] = None
        self.assertEqual(tool.differences(before, after)["changed_parent_links"], 1)

    def test_capture_mismatch_stops_without_writing(self):
        output = Path(self.directory.name) / "none.json"
        status = tool.main([
            "capture", "--config", str(self.config), "--output", str(output),
            "--expected-entities", "72",
        ])
        self.assertEqual(status, 2)
        self.assertFalse(output.exists())

    def test_snapshot_file_created_private_and_not_overwritten(self):
        baseline = tool.capture(self.config)
        file = Path(self.directory.name) / "baseline.json"
        tool.save_private_snapshot(file, baseline)
        self.assertEqual(file.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(file.read_text())["format"], tool.SNAPSHOT_FORMAT)
        with self.assertRaises(FileExistsError):
            tool.save_private_snapshot(file, baseline)

    def test_duplicate_entity_registry_identity_is_rejected(self):
        file = self.config / ".storage" / "core.entity_registry"
        registry = json.loads(file.read_text())
        duplicate = copy.deepcopy(registry["data"]["entities"][0])
        duplicate["entity_id"] = "sensor.duplicate"
        registry["data"]["entities"].append(duplicate)
        file.write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            tool.capture(self.config)

    def test_missing_config_entry_fails_closed(self):
        file = self.config / ".storage" / "core.config_entries"
        registry = json.loads(file.read_text())
        registry["data"]["entries"][0]["domain"] = "not_euros"
        file.write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError, "No config entry"):
            tool.capture(self.config)

    def test_compare_command_reports_diff_without_leaking_identifiers(self):
        before = tool.capture(self.config)
        after = copy.deepcopy(before)
        after["entities"][0]["entity_id"] = "sensor.changed_private"
        base = Path(self.directory.name) / "before.json"
        new = Path(self.directory.name) / "after.json"
        base.write_text(json.dumps(before))
        new.write_text(json.dumps(after))
        self.assertEqual(tool.main([
            "compare", "--before", str(base), "--after", str(new)
        ]), 2)


if __name__ == "__main__":
    unittest.main()
