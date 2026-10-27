"""Unit tests for GEO-specific, dependency-free sensor helpers."""

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "euros_os"
    / "geo.py"
)
spec = importlib.util.spec_from_file_location("euros_geo", MODULE_PATH)
geo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)


class GeoSensorTests(unittest.TestCase):
    def test_geo_names_are_model_specific(self):
        original = ("Temp. powietrza zasysanego", "°C", "mdi:thermometer", "temperature")
        self.assertEqual(
            geo.sensor_info_for_device("T3fiz", original, "FriskoGEO")[0],
            "Dolne źródło — temperatura powrotu z gruntu",
        )
        self.assertEqual(geo.sensor_info_for_device("T3fiz", original, "Other"), original)
        self.assertEqual(geo.sensor_info_for_device("T3fiz", original, None), original)
        self.assertEqual(geo.sensor_info_for_device("OTHER", original, "FriskoGEO"), original)

    def test_storage_tank_names_geo_only(self):
        originals = {
            "TSM15": ("Temp. zbiornika CWU", "°C", "mdi:thermometer", "temperature"),
            "TSM17": ("Temp. zbiornika buforowego", "°C", "mdi:thermometer", "temperature"),
        }
        expected = {
            "TSM15": "CWU — temperatura zbiornika",
            "TSM17": "Bufor CO — temperatura zbiornika",
        }
        for key, original in originals.items():
            self.assertEqual(
                geo.sensor_info_for_device(key, original, geo.GEO_DEVICE_TYPE)[0],
                expected[key],
            )
            self.assertEqual(
                geo.sensor_info_for_device(key, original, "Other"), original
            )

    def test_ground_source_labels_sort_together(self):
        original = ("Original", "°C", "mdi:thermometer", "temperature")
        names = [
            geo.sensor_info_for_device(key, original, geo.GEO_DEVICE_TYPE)[0]
            for key in ("T3fiz", "T4fiz")
        ]
        names.append(geo.GEO_GROUND_SOURCE_DELTA_T_NAME)
        self.assertEqual(
            sorted(names),
            [
                "Dolne źródło — temperatura powrotu z gruntu",
                "Dolne źródło — temperatura różnicowa (ΔT)",
                "Dolne źródło — temperatura wyjścia do gruntu",
            ],
        )

    def test_upper_source_labels_sort_together(self):
        original = ("Original", "°C", "mdi:thermometer", "temperature")
        labels = [
            geo.sensor_info_for_device(key, original, geo.GEO_DEVICE_TYPE)[0]
            for key in ("T5fiz", "TSM13")
        ]
        labels.append(geo.GEO_UPPER_SOURCE_DELTA_T_NAME)
        self.assertEqual(
            sorted(labels),
            [
                "Górne źródło — temperatura powrotu",
                "Górne źródło — temperatura różnicowa (ΔT)",
                "Górne źródło — temperatura zasilania",
            ],
        )
        self.assertEqual(
            geo.sensor_info_for_device("T5fiz", original, "Other"), original
        )

    def test_upper_source_delta(self):
        self.assertEqual(
            geo.calculate_upper_source_delta_t({"TSM13": 27.4, "T5fiz": 22.3}),
            5.1,
        )
        self.assertEqual(
            geo.calculate_upper_source_delta_t({"TSM13": 19.1, "T5fiz": 20.2}),
            -1.1,
        )
        self.assertIsNone(geo.calculate_upper_source_delta_t({"TSM13": 27.4}))
        self.assertIsNone(
            geo.calculate_upper_source_delta_t({"TSM13": "nan", "T5fiz": 22.3})
        )

    def test_delta_positive_and_negative(self):
        self.assertEqual(geo.calculate_ground_source_delta_t({"T3fiz": "10.9", "T4fiz": "8.8"}), 2.1)
        self.assertEqual(geo.calculate_ground_source_delta_t({"T3fiz": "2", "T4fiz": "4"}), -2.0)

    def test_delta_missing_invalid_or_out_of_range(self):
        self.assertIsNone(geo.calculate_ground_source_delta_t({"T3fiz": "10"}))
        self.assertIsNone(geo.calculate_ground_source_delta_t({"T3fiz": "bad", "T4fiz": "8"}))
        self.assertIsNone(geo.calculate_ground_source_delta_t({"T3fiz": "nan", "T4fiz": "8"}))
        self.assertIsNone(geo.calculate_ground_source_delta_t({"T3fiz": "150", "T4fiz": "8"}))


if __name__ == "__main__":
    unittest.main()
