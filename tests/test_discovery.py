"""Pure discovery tests; no Home Assistant runtime required."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "custom_components" / "euros_os" / "discovery.py"
spec = importlib.util.spec_from_file_location("euros_os_discovery_test", MODULE)
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


def pump(name="GEO_1", kind="FriskoGEO"):
    return {"Name": name, "Type": kind, "Data": {"STATE": "1"}}


class PumpDiscoveryTests(unittest.TestCase):
    def test_all_supported_models(self):
        for name, kind in (("GEO_1", "FriskoGEO"), ("ATMO_1", "FriskoATMO"),
                           ("ALLINONE_1", "FriskoALLINONE")):
            with self.subTest(kind=kind):
                self.assertEqual(discovery.find_pump([pump(name, kind)]), pump(name, kind))

    def test_meter_before_pump(self):
        meter = {"Name": "METER_1", "Type": "METER", "Data": {}}
        self.assertEqual(discovery.find_pump([meter, pump()]), pump())

    def test_no_pump_or_unknown_model(self):
        self.assertIsNone(discovery.find_pump([{"Name": "METER_1", "Type": "METER", "Data": {}}]))
        self.assertIsNone(discovery.find_pump([pump(kind="Unknown")]))

    def test_ambiguous_pumps_require_identity(self):
        devices = [pump(), pump("ALLINONE_1", "FriskoALLINONE")]
        self.assertIsNone(discovery.find_pump(devices))
        self.assertEqual(discovery.find_pump(devices, expected_name="GEO_1",
                                             expected_type="FriskoGEO"), pump())

    def test_reject_malformed_devices(self):
        for devices in (None, {}, [], [None], [{"Name": "GEO_1", "Type": "FriskoGEO"}],
                        [pump(), pump()]):
            with self.subTest(devices=devices):
                self.assertIsNone(discovery.find_pump(devices))

    def test_identity_does_not_switch_pumps(self):
        self.assertIsNone(discovery.find_pump([pump("GEO_2")],
                                               expected_name="GEO_1",
                                               expected_type="FriskoGEO"))


if __name__ == "__main__":
    unittest.main()
