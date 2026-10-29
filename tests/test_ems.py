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

    def test_daily_counter_starts_from_physical_meter_baseline(self):
        day, total, last = ems.accumulate_ems_daily_energy(
            "2026-10-29", None, None, "2026-10-29", "319.28"
        )
        self.assertEqual((day, total, last), ("2026-10-29", 0.0, 319.28))
        day, total, last = ems.accumulate_ems_daily_energy(
            day, total, last, "2026-10-29", "319.37"
        )
        self.assertAlmostEqual(total, 0.09)
        day, total, last = ems.accumulate_ems_daily_energy(
            day, total, last, "2026-10-29", "319.37"
        )
        self.assertAlmostEqual(total, 0.09)

    def test_daily_counter_rollover_on_local_calendar_day(self):
        day, total, last = ems.accumulate_ems_daily_energy(
            "2026-10-29", 2.31, 321.59, "2026-10-30", 321.61
        )
        self.assertEqual((day, total, last), ("2026-10-30", 0.0, 321.61))
        day, total, last = ems.accumulate_ems_daily_energy(
            day, total, last, "2026-10-30", 321.66
        )
        self.assertAlmostEqual(total, 0.05)

    def test_midnight_timer_preserves_last_meter_counter(self):
        # A scheduled midnight reset sets today's total to zero, but leaves
        # the last lifetime reading so the first increment is not lost.
        day, total, last = ems.accumulate_ems_daily_energy(
            "2026-10-30", 0.0, 321.59, "2026-10-30", 321.61
        )
        self.assertEqual((day, total), ("2026-10-30", 0.02))
        self.assertEqual(last, 321.61)

    def test_daily_counter_restart_restores_accumulated_state(self):
        day, total, last = ems.accumulate_ems_daily_energy(
            "2026-10-29", 1.23, 319.28, "2026-10-29", 319.37
        )
        self.assertEqual(day, "2026-10-29")
        self.assertAlmostEqual(total, 1.32)
        self.assertEqual(last, 319.37)

    def test_daily_counter_ignores_bad_or_negative_measurements(self):
        prior = ("2026-10-29", 0.21, 10067.82)
        for invalid in (None, "unknown", float("nan"), "-1", True):
            self.assertEqual(
                ems.accumulate_ems_daily_energy(*prior, "2026-10-29", invalid),
                prior,
            )

    def test_daily_counter_ignores_small_fall_and_rebases_big_reset(self):
        prior = ("2026-10-29", 0.5, 10067.82)
        self.assertEqual(
            ems.accumulate_ems_daily_energy(*prior, "2026-10-29", 10067.81),
            prior,
        )
        day, total, last = ems.accumulate_ems_daily_energy(
            *prior, "2026-10-29", 0.0
        )
        self.assertEqual((day, total, last), ("2026-10-29", 0.5, 0.0))
        day, total, last = ems.accumulate_ems_daily_energy(
            day, total, last, "2026-10-29", 0.1
        )
        self.assertAlmostEqual(total, 0.6)

    def test_missing_meter_packet_clears_snapshot(self):
        self.assertEqual(
            ems.extract_ems_meters([{"Name": "GEO_1", "Type": "FriskoGEO", "Data": {}}]),
            {},
        )


if __name__ == "__main__":
    unittest.main()
