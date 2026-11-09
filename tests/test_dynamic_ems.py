"""Stage 5: dynamic METER_N discovery without a broker or real Home Assistant."""
import asyncio
from datetime import datetime
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "euros_os"


def mod(name, **fields):
    result = types.ModuleType(name)
    result.__dict__.update(fields)
    return result


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


class EmsHelperDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ems = load("test_stage5_ems_helpers", "ems.py")

    def test_meter_one_keeps_all_existing_keys_and_names(self):
        ems = self.ems
        valid_meter = {"TOTAL_ACT_POW_FL_1": "0.025"}
        self.assertEqual(len(ems.discover_ems_sensor_keys("METER_1", valid_meter)), 33)
        self.assertEqual(len(ems.discover_ems_daily_keys("METER_1", valid_meter)), 2)
        self.assertEqual(ems.discover_ems_sensor_keys("METER_1", {}), ())
        self.assertEqual(ems.discover_ems_daily_keys("METER_1", {}), ())
        self.assertEqual(ems.ems_meter_device_name("METER_1"), "EMS – Dom")
        self.assertEqual(ems.ems_meter_sensor_info(
            "METER_1", "TOTAL_ACT_POW_FL_1"), ems.EMS_DOM_SENSOR_DEFINITIONS["TOTAL_ACT_POW_FL_1"])

    def test_second_meter_only_valid_reported_fields(self):
        ems = self.ems
        keys = ems.discover_ems_sensor_keys("METER_2", {
            "TOTAL_ACT_POW_FL_1": "0.125",
            "A_PHA_VOLT_FL_1": "invalid",
            "POS_ACT_POW_FL_1": None,
            "NOT_SUPPORTED": 10,
        })
        self.assertEqual(keys, ("TOTAL_ACT_POW_FL_1",))
        self.assertEqual(ems.discover_ems_daily_keys("METER_2", {"POS_ACT_POW_FL_1": 20}), ())
        self.assertEqual(ems.ems_meter_device_name("METER_2"), "EMS – METER_2")
        self.assertEqual(ems.ems_meter_sensor_info("METER_2", "TOTAL_ACT_POW_FL_1")[0],
                         "EMS – METER_2 – TOTAL_ACT_POW_FL_1")

    def test_invalid_reading_is_not_zero(self):
        self.assertEqual(self.ems.discover_ems_sensor_keys("METER_3", {"TOTAL_ACT_POW_FL_1": ""}), ())
        self.assertEqual(self.ems.discover_ems_sensor_keys("METER_3", {"TOTAL_ACT_POW_FL_1": "0"}), ("TOTAL_ACT_POW_FL_1",))


class FakeCoordinator:
    def __init__(self):
        self.ems_meters = {}
        self._meter_last_update = {}
        self.listeners = []
        self.device = {}
        self._last_update = None

    def async_add_listener(self, listener):
        self.listeners.append(listener)

    def async_remove_listener(self, listener):
        self.listeners.remove(listener)

    def emit(self):
        for listener in tuple(self.listeners):
            listener()


class Registry:
    def __init__(self):
        self.calls = []

    def async_get_or_create(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(id="pump_registry_id")


class DynamicEmsPlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        fake_emsc = mod("custom_components.euros_os.ems")
        cls.patch_modules = patch.dict(sys.modules, {
            "homeassistant": mod("homeassistant"),
            "homeassistant.components": mod("homeassistant.components"),
            "homeassistant.components.sensor": mod("homeassistant.components.sensor",
                SensorEntity=type("SensorEntity", (), {"hass": None}),
                RestoreSensor=type("RestoreSensor", (), {"hass": None})),
            "homeassistant.helpers": mod("homeassistant.helpers"),
            "homeassistant.helpers.device_registry": mod(
                "homeassistant.helpers.device_registry", async_get=lambda hass: cls.registry),
            "homeassistant.helpers.entity": mod("homeassistant.helpers.entity",
                EntityCategory=types.SimpleNamespace(DIAGNOSTIC="diagnostic")),
            "homeassistant.helpers.event": mod("homeassistant.helpers.event",
                async_track_time_change=lambda *args, **kwargs: lambda: None),
            "homeassistant.util": mod("homeassistant.util"),
            "homeassistant.util.dt": mod("homeassistant.util.dt",
                now=lambda: datetime(2026, 11, 9)),
            "homeassistant.core": mod("homeassistant.core", callback=lambda fn: fn),
            "custom_components": mod("custom_components"),
            "custom_components.euros_os": mod("custom_components.euros_os"),
            "custom_components.euros_os.const": mod(
                "custom_components.euros_os.const",
                DOMAIN="euros_os", CONF_KEY="key", CONF_IP="ip",
                SENSORS_VARIABLES={}, MQTT_TIMEOUT=60),
            "custom_components.euros_os.coordinator": mod(
                "custom_components.euros_os.coordinator",
                EurosOSMQTTCoordinator=FakeCoordinator),
            "custom_components.euros_os.geo": mod(
                "custom_components.euros_os.geo",
                GEO_DEVICE_TYPE="FriskoGEO",
                GEO_GROUND_SOURCE_DELTA_T="GEO_DELTA_1",
                GEO_GROUND_SOURCE_DELTA_T_NAME="Delta 1",
                GEO_UPPER_SOURCE_DELTA_T="GEO_DELTA_2",
                GEO_UPPER_SOURCE_DELTA_T_NAME="Delta 2",
                calculate_ground_source_delta_t=lambda *args: None,
                calculate_upper_source_delta_t=lambda *args: None,
                calculate_geo_operating_state=lambda *args: None,
                entity_supported_for_device=lambda *args: True,
                sensor_info_for_device=lambda key, info, device_type: info),
        })
        cls.patch_modules.start()
        load("custom_components.euros_os.ems", "ems.py")
        cls.sensor = load("custom_components.euros_os.sensor", "sensor.py")

    @classmethod
    def tearDownClass(cls):
        cls.patch_modules.stop()

    def setUp(self):
        self.registry.calls.clear()
        self.coordinator = FakeCoordinator()
        self.entry = types.SimpleNamespace(entry_id="entry")
        self.state = {
            "entry_data": {"key": "abcdef", "device_type": "FriskoALLINONE"},
            "coordinator": self.coordinator,
            "device_info": {"identifiers": {("euros_os", "abcdef")}, "name": "pump"},
        }
        self.hass = types.SimpleNamespace(data={"euros_os": {"entry": self.state}})
        self.batches = []

    def setup_platform(self, pump_type="FriskoALLINONE"):
        self.state["entry_data"]["device_type"] = pump_type
        asyncio.run(self.sensor.async_setup_entry(
            self.hass, self.entry, lambda entities: self.batches.append(entities)
        ))

    def test_allinone_without_meter_has_no_ems_and_no_fake_device(self):
        self.setup_platform()
        self.assertEqual(self.batches, [[]])
        self.assertEqual(self.registry.calls, [])
        self.assertEqual(len(self.coordinator.listeners), 1)

    def test_meters_appear_dynamically_without_restart_or_duplicates(self):
        self.setup_platform()
        self.coordinator.ems_meters = {"METER_2": {"TOTAL_ACT_POW_FL_1": "0.05"}}
        self.coordinator.emit()
        self.assertEqual(len(self.batches[-1]), 1)
        entity = self.batches[-1][0]
        self.assertEqual(entity._attr_unique_id, "abcdef_ems_meter_2_total_act_pow_fl_1")
        self.assertEqual(entity._attr_device_info["identifiers"], {("euros_os", "abcdef_ems_meter_2")})
        self.assertEqual(entity._attr_device_info["via_device_id"], "pump_registry_id")
        self.coordinator.emit()
        self.assertEqual(len(self.batches), 2)
        self.coordinator.ems_meters["METER_2"]["A_PHA_VOLT_FL_1"] = "231.2"
        self.coordinator.emit()
        self.assertEqual(len(self.batches), 3)
        self.assertEqual(self.batches[-1][0]._attr_unique_id,
                         "abcdef_ems_meter_2_a_pha_volt_fl_1")
        self.assertEqual(len(self.registry.calls), 1)

    def test_meter_one_retains_legacy_ids_and_daily_sensors(self):
        self.coordinator.ems_meters = {"METER_1": {"TOTAL_ACT_POW_FL_1": "0.025"}}
        self.setup_platform("FriskoGEO")
        ems_entities = [entity for entity in self.batches[0]
                        if getattr(entity, "meter_name", None) == "METER_1"]
        self.assertEqual(len(ems_entities), 35)
        ids = {entity._attr_unique_id for entity in ems_entities}
        self.assertIn("abcdef_ems_meter_1_total_act_pow_fl_1", ids)
        self.assertIn("abcdef_ems_meter_1_daily_pos_act_pow_fl_1", ids)
        self.assertEqual(ems_entities[0]._attr_device_info["name"], "EMS – Dom")

    def test_meter_temporarily_missing_does_not_remove_registered_entities(self):
        self.setup_platform()
        self.coordinator.ems_meters = {"METER_3": {"TOTAL_ACT_POW_FL_1": 1.0}}
        self.coordinator.emit()
        count = len(self.batches)
        self.coordinator.ems_meters = {}
        self.coordinator.emit()
        self.assertEqual(len(self.batches), count)
        self.coordinator.ems_meters = {"METER_3": {"TOTAL_ACT_POW_FL_1": 2.0}}
        self.coordinator.emit()
        self.assertEqual(len(self.batches), count)

    def test_reloading_platform_reuses_legacy_unique_ids(self):
        # A new coordinator and fresh entities use the same unique IDs, so
        # HA's entity registry can reuse historic METER_1 entities/history.
        self.coordinator.ems_meters = {
            "METER_1": {"TOTAL_ACT_POW_FL_1": "0.100"}
        }
        self.setup_platform("FriskoGEO")
        first = {
            entity._attr_unique_id
            for entity in self.batches[0]
            if getattr(entity, "meter_name", None) == "METER_1"
        }
        self.assertEqual(len(first), 35)
        self.coordinator = FakeCoordinator()
        self.coordinator.ems_meters = {
            "METER_1": {"TOTAL_ACT_POW_FL_1": "0.200"}
        }
        self.state["coordinator"] = self.coordinator
        self.setup_platform("FriskoGEO")
        second = {
            entity._attr_unique_id
            for entity in self.batches[-1]
            if getattr(entity, "meter_name", None) == "METER_1"
        }
        self.assertEqual(first, second)
        self.assertIn("abcdef_ems_meter_1_daily_rew_act_pow_fl_1", second)

    def test_reloading_platform_reuses_additional_meter_unique_ids(self):
        self.coordinator.ems_meters = {
            "METER_2": {"TOTAL_ACT_POW_FL_1": "0.100"}
        }
        self.setup_platform()
        first = [
            entity._attr_unique_id for entity in self.batches[0]
            if getattr(entity, "meter_name", None) == "METER_2"
        ]
        self.coordinator = FakeCoordinator()
        self.coordinator.ems_meters = {
            "METER_2": {"TOTAL_ACT_POW_FL_1": "0.200"}
        }
        self.state["coordinator"] = self.coordinator
        self.setup_platform()
        second = [
            entity._attr_unique_id for entity in self.batches[-1]
            if getattr(entity, "meter_name", None) == "METER_2"
        ]
        self.assertEqual(first, second)
        self.assertEqual(first, ["abcdef_ems_meter_2_total_act_pow_fl_1"])

    def test_meter_available_by_own_freshness_not_stale_pump(self):
        self.setup_platform()
        self.coordinator.ems_meters = {"METER_2": {"TOTAL_ACT_POW_FL_1": "1"}}
        self.coordinator.emit()
        entity = self.batches[-1][0]
        import time
        self.coordinator._meter_last_update["METER_2"] = time.time()
        self.assertTrue(entity.available)
        self.coordinator._meter_last_update["METER_2"] -= 120
        self.assertFalse(entity.available)
        self.coordinator._meter_last_update["METER_2"] = time.time()
        self.coordinator.ems_meters = {}
        self.assertFalse(entity.available)


if __name__ == "__main__":
    unittest.main()
