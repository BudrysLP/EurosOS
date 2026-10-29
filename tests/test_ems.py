"""Unit tests for the read-only EMS whole-home meter helpers."""

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "euros_os"
    / "ems.py"
)
spec = importlib.util.spec_from_file_location("euros_ems", MODULE_PATH)
ems = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ems)


class EmsMeterTests(unittest.TestCase):
    def test_exactly_ten_home_meter_sensors(self):
        self.assertEqual(len(ems.EMS_DOM_SENSOR_DEFINITIONS), 10)
        self.assertEqual(ems.EMS_DOM_DEVICE_NAME, "EMS – Dom")
        self.assertEqual(ems.EMS_DOM_METER_NAME, "METER_1")

    def test_energy_counters_are_kwh_and_total_increasing(self):
        for key in ("POS_ACT_POW_FL_1", "REW_ACT_POW_FL_1"):
            self.assertEqual(ems.EMS_DOM_SENSOR_DEFINITIONS[key][1], "kWh")
            self.assertEqual(ems.EMS_DOM_SENSOR_DEFINITIONS[key][4], "total_increasing")

    def test_signed_grid_power_is_preserved(self):
        self.assertEqual(ems.parse_ems_numeric("2.01"), 2.01)
        self.assertEqual(ems.parse_ems_numeric("-0.125"), -0.125)
        self.assertEqual(ems.parse_ems_numeric("0"), 0.0)

    def test_missing_or_invalid_reading_is_not_a_false_zero(self):
        for value in (None, "", "unavailable", "NaN", "inf", "-inf", True, {}, []):
            self.assertIsNone(ems.parse_ems_numeric(value))

    def test_separates_geo_and_multiple_meter_devices(self):
        devices = [
            {"Name": "GEO_1", "Type": "FriskoGEO", "Data": {"TSM16": "24.2"}},
            {"Name": "METER_1", "Type": "METER", "Data": {
                "TOTAL_ACT_POW_FL_1": "0.168",
                "POS_ACT_POW_FL_1": "318.44",
                "REW_ACT_POW_FL_1": "10067.75",
            }},
            {"Name": "METER_2", "Type": "METER", "Data": {"TOTAL_ACT_POW_FL_1": "1"}},
        ]
        meters = ems.extract_ems_meters(devices)
        self.assertEqual(set(meters), {"METER_1", "METER_2"})
        self.assertEqual(ems.parse_ems_numeric(meters["METER_1"]["TOTAL_ACT_POW_FL_1"]), 0.168)
        self.assertNotIn("GEO_1", meters)

    def test_rejects_invalid_or_spoofed_meter(self):
        devices = [
            {"Name": "METER_1", "Type": "FriskoGEO", "Data": {"TOTAL_ACT_POW_FL_1": "999"}},
            {"Name": "WRONG", "Type": "METER", "Data": {"TOTAL_ACT_POW_FL_1": "999"}},
            {"Name": "METER_3", "Type": "METER", "Data": None},
            "bad",
        ]
        self.assertEqual(ems.extract_ems_meters(devices), {})
        self.assertEqual(ems.extract_ems_meters(None), {})

    def test_missing_meter_packet_clears_snapshot(self):
        self.assertEqual(
            ems.extract_ems_meters([{"Name": "GEO_1", "Type": "FriskoGEO", "Data": {}}]),
            {},
        )


if __name__ == "__main__":
    unittest.main()
