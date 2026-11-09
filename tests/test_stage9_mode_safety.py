"""Stage 9: exercise GEO EMS controls without sending commands to hardware."""
import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "euros_os"


def module(name, **attrs):
    result = types.ModuleType(name)
    result.__dict__.update(attrs)
    return result


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


class HaError(Exception):
    pass


class ModeSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patches = patch.dict(sys.modules, {
            "homeassistant": module("homeassistant"),
            "homeassistant.components": module("homeassistant.components"),
            "homeassistant.components.number": module(
                "homeassistant.components.number",
                NumberEntity=type("NumberEntity", (), {"hass": None}),
                NumberMode=types.SimpleNamespace(AUTO="auto", SLIDER="slider", BOX="box"),
            ),
            "homeassistant.components.select": module(
                "homeassistant.components.select",
                SelectEntity=type("SelectEntity", (), {"hass": None}),
            ),
            "homeassistant.exceptions": module("homeassistant.exceptions", HomeAssistantError=HaError),
            "homeassistant.core": module("homeassistant.core", callback=lambda fn: fn),
            "custom_components": module("custom_components"),
            "custom_components.euros_os": module("custom_components.euros_os"),
            "custom_components.euros_os.const": module(
                "custom_components.euros_os.const",
                DOMAIN="euros_os", CONF_KEY="key",
                NUMBERS_VARIABLES={}, SELECTS_VARIABLES={},
            ),
            "custom_components.euros_os.coordinator": module(
                "custom_components.euros_os.coordinator", EurosOSMQTTCoordinator=object,
            ),
            "custom_components.euros_os.geo": module(
                "custom_components.euros_os.geo",
                GEO_DEVICE_TYPE="FriskoGEO",
                entity_supported_for_device=lambda *a: True,
            ),
        })
        cls.patches.start()
        cls.number_module = load("custom_components.euros_os.number", "number.py")
        cls.select_module = load("custom_components.euros_os.select", "select.py")

    @classmethod
    def tearDownClass(cls):
        cls.patches.stop()

    def setUp(self):
        self.sent = []
        async def send(data, entry_data):
            self.sent.append(data)
            return True
        self.coordinator = types.SimpleNamespace(
            pump_type="FriskoGEO",
            device={"Data": {
                "SBF_OOF": 1, "SXF_ECO": 0, "SXF_AWA": 0,
                "SXF_TIME": 0, "U_ENE_TAR": 1,
            }},
            entry_data={"device_model": "GEO_1"},
            async_add_listener=lambda fn: None,
            async_set_device_value=send,
        )
        self.temp = self.number_module.EurosOSNumber(
            self.coordinator, "SPDHW_ZAD",
            ("Target CWU", "°C", "mdi:thermometer", 30, 55, 1, "BOX"),
            "site", {},
        )
        self.mode = self.select_module.EurosOSModeSelect(
            self.coordinator, "MODE",
            ("Mode", None, "mdi:autorenew", ["AUTO", "ECO", "TIME", "AWAY", "OFF"]),
            "site", {}, device_type="FriskoGEO",
        )

    def test_geo_ems_is_not_misidentified_as_auto(self):
        self.assertEqual(self.temp._get_device_mode(), "EMS")
        self.assertEqual(self.mode.current_option, "EMS")

    def test_user_temperature_adjustment_remains_available_in_ems(self):
        asyncio.run(self.temp.async_set_native_value(50))
        self.assertEqual(self.sent, [{"SPDHW_ZAD": 50}])
        self.assertNotIn("U_ENE_TAR", self.sent[0])

    def test_auto_temperature_control_is_still_supported(self):
        self.coordinator.device["Data"]["U_ENE_TAR"] = 0
        self.assertEqual(self.temp._get_device_mode(), "AUTO")
        asyncio.run(self.temp.async_set_native_value(49))
        self.assertEqual(self.sent, [{"SPDHW_ZAD": 49}])

    def test_invalid_tariff_never_guesses_auto_or_emits_temperature(self):
        for bad in (None, "bad", "", 2, True):
            with self.subTest(bad=bad):
                self.coordinator.device["Data"]["U_ENE_TAR"] = bad
                self.assertEqual(self.temp._get_device_mode(), "UNKNOWN")
                with self.assertRaises(HaError):
                    asyncio.run(self.temp.async_set_native_value(50))
        self.assertEqual(self.sent, [])

    def test_other_modes_reject_temperature_changes(self):
        self.coordinator.device["Data"]["U_ENE_TAR"] = 0
        self.coordinator.device["Data"]["SXF_TIME"] = 1
        with self.assertRaises(HaError):
            asyncio.run(self.temp.async_set_native_value(50))
        self.assertEqual(self.sent, [])

    def test_unverified_ems_transition_is_blocked_without_publish(self):
        with self.assertRaises(HaError):
            asyncio.run(self.mode.async_select_option("EMS"))
        with self.assertRaises(HaError):
            asyncio.run(self.mode.async_select_option("AUTO"))
        self.assertEqual(self.sent, [])

    def test_legacy_non_geo_mode_without_tariff_still_auto(self):
        self.coordinator.pump_type = "FriskoATMO"
        self.coordinator.device["Data"].pop("U_ENE_TAR")
        self.assertEqual(self.temp._get_device_mode(), "AUTO")


if __name__ == "__main__":
    unittest.main()
