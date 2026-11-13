"""Coordinator integration-style tests using a fake MQTT client and HA stubs.

Run: python -m unittest discover -s tests -p 'test_coordinator_discovery.py'
No broker, Home Assistant installation, or real device is required.
"""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "euros_os"


def module(name, **attrs):
    obj = types.ModuleType(name)
    obj.__dict__.update(attrs)
    return obj


class FakeLoop:
    def __init__(self):
        self.pending = []
        self.closed = False

    def is_closed(self):
        return self.closed

    def call_soon_threadsafe(self, fn, *args):
        self.pending.append((fn, args))

    def flush(self):
        while self.pending:
            fn, args = self.pending.pop(0)
            fn(*args)


class FakeClient:
    instances = []

    def __init__(self):
        self.published = []
        self.subscribed = []
        self.disconnect_calls = 0
        self.loop_stop_calls = 0
        FakeClient.instances.append(self)

    def username_pw_set(self, *args):
        pass

    def tls_set_context(self, *args):
        pass

    def connect(self, *args):
        self.on_connect(self, None, None, 0)

    def subscribe(self, topic):
        self.subscribed.append(topic)

    def loop_start(self):
        pass

    def loop_stop(self):
        self.loop_stop_calls += 1

    def disconnect(self):
        self.disconnect_calls += 1

    def emit(self, devices):
        self.on_message(self, None, types.SimpleNamespace(
            payload=json.dumps({"Devices": devices}).encode()
        ))

    def publish(self, *args, **kwargs):
        self.published.append((args, kwargs))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


class CoordinatorDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch_modules = patch.dict(sys.modules, {
            "homeassistant": module("homeassistant"),
            "homeassistant.helpers": module("homeassistant.helpers"),
            "homeassistant.helpers.update_coordinator": module(
                "homeassistant.helpers.update_coordinator",
                DataUpdateCoordinator=type("DataUpdateCoordinator", (), {
                    "__init__": lambda self, *a, **k: None,
                }),
            ),
            "homeassistant.core": module("homeassistant.core", callback=lambda fn: fn),
            "paho": module("paho"),
            "paho.mqtt": module("paho.mqtt"),
            "paho.mqtt.client": module("paho.mqtt.client", Client=FakeClient),
            "custom_components": module("custom_components"),
            "custom_components.euros_os": module("custom_components.euros_os"),
            "custom_components.euros_os.const": module(
                "custom_components.euros_os.const",
                MQTT_PORT=8883, MQTT_USER="test", MQTT_PASSWORD="test",
            ),
        })
        cls.patch_modules.start()
        load("custom_components.euros_os.discovery", "discovery.py")
        load("custom_components.euros_os.ems", "ems.py")
        cls.coordinator_module = load("custom_components.euros_os.coordinator", "coordinator.py")

    @classmethod
    def tearDownClass(cls):
        cls.patch_modules.stop()

    def setUp(self):
        FakeClient.instances.clear()
        self.loop = FakeLoop()
        self.coordinator = self.coordinator_module.EurosOSMQTTCoordinator(
            "127.0.0.1", "test/Dev",
            pump_name="GEO_1", pump_type="FriskoGEO", event_loop=self.loop,
        )
        self.events = []
        self.coordinator.async_add_listener(lambda: self.events.append("updated"))
        self.coordinator.connect()
        self.client = FakeClient.instances[-1]

    @staticmethod
    def geo():
        return {"Name": "GEO_1", "Type": "FriskoGEO", "Data": {"TSM16": "24.2"}}

    @staticmethod
    def meter(power="0.168"):
        return {"Name": "METER_1", "Type": "METER", "Data": {
            "TOTAL_ACT_POW_FL_1": power, "POS_ACT_POW_FL_1": "319.37",
        }}

    def test_geo_ems_in_either_order(self):
        for devices in ([self.meter(), self.geo()], [self.geo(), self.meter()]):
            self.client.emit(devices)
            self.assertEqual(self.coordinator.device["Name"], "GEO_1")
            self.assertEqual(self.coordinator.ems_meters["METER_1"]["TOTAL_ACT_POW_FL_1"], "0.168")
        self.assertEqual(self.events, [])  # No HA callbacks on MQTT thread
        self.loop.flush()
        self.assertEqual(len(self.events), 2)
        self.assertEqual(self.client.published, [])

    def test_no_meter_does_not_create_phantom_meter(self):
        self.client.emit([self.geo()])
        self.assertEqual(self.coordinator.ems_meters, {})

    def test_meter_only_does_not_overwrite_pump_or_last_update(self):
        self.client.emit([self.geo(), self.meter()])
        previous = self.coordinator._last_update
        self.client.emit([self.meter("2.0")])
        self.assertEqual(self.coordinator._last_update, previous)
        self.assertEqual(self.coordinator.device["Name"], "GEO_1")
        self.assertEqual(self.coordinator.ems_meters["METER_1"]["TOTAL_ACT_POW_FL_1"], "2.0")
        self.assertIn("METER_1", self.coordinator._meter_last_update)

    def test_meter_only_packet_can_discover_new_meter(self):
        self.client.emit([self.geo(), self.meter()])
        previous = self.coordinator._last_update
        meter2 = {"Name": "METER_2", "Type": "METER", "Data": {"TOTAL_ACT_POW_FL_1": "0.03"}}
        self.client.emit([meter2])
        self.assertEqual(self.coordinator.device["Name"], "GEO_1")
        self.assertEqual(self.coordinator._last_update, previous)
        self.assertEqual(set(self.coordinator.ems_meters), {"METER_1", "METER_2"})
        self.assertIn("METER_2", self.coordinator._meter_last_update)

    def test_foreign_pump_cannot_inject_meter(self):
        self.client.emit([self.geo(), self.meter()])
        foreign = {"Name": "ALLINONE_1", "Type": "FriskoALLINONE", "Data": {}}
        injected = {"Name": "METER_3", "Type": "METER", "Data": {"TOTAL_ACT_POW_FL_1": "9"}}
        self.client.emit([foreign, injected])
        self.assertNotIn("METER_3", self.coordinator.ems_meters)
        self.assertEqual(self.coordinator.device["Name"], "GEO_1")

    def test_pump_snapshot_without_meter_clears_active_readings_not_entity_registry(self):
        self.client.emit([self.geo(), self.meter()])
        self.assertIn("METER_1", self.coordinator.ems_meters)
        self.client.emit([self.geo()])
        self.assertEqual(self.coordinator.ems_meters, {})
        self.assertEqual(self.coordinator._meter_last_update, {})

    def test_unknown_or_other_pump_does_not_switch(self):
        self.client.emit([self.geo()])
        previous = self.coordinator._last_update
        self.client.emit([{"Name": "ALLINONE_1", "Type": "FriskoALLINONE", "Data": {}}])
        self.assertEqual(self.coordinator.device["Name"], "GEO_1")
        self.assertEqual(self.coordinator._last_update, previous)

    def test_restart_same_identity_without_duplicates(self):
        self.client.emit([self.geo(), self.meter()])
        self.loop.flush()
        self.coordinator.async_remove_listener(self.coordinator._listeners[0])
        self.assertEqual(self.coordinator._listeners, [])
        restarted = self.coordinator_module.EurosOSMQTTCoordinator(
            "127.0.0.1", "test/Dev",
            pump_name="GEO_1", pump_type="FriskoGEO", event_loop=self.loop,
        )
        restarted.connect()
        FakeClient.instances[-1].emit([self.meter(), self.geo()])
        self.assertEqual(restarted.device["Name"], "GEO_1")
        self.assertEqual(set(restarted.ems_meters), {"METER_1"})

    def test_unload_disconnects_worker_without_destroying_snapshots(self):
        self.client.emit([self.geo(), self.meter()])
        self.loop.flush()
        old_pump = self.coordinator.device
        old_meters = self.coordinator.ems_meters
        self.coordinator.disconnect()
        self.assertIsNone(self.coordinator.client)
        self.assertFalse(self.coordinator.connected.is_set())
        self.assertEqual(self.client.disconnect_calls, 1)
        self.assertEqual(self.client.loop_stop_calls, 1)
        self.assertIs(self.coordinator.device, old_pump)
        self.assertIs(self.coordinator.ems_meters, old_meters)
        self.client.emit([self.geo(), self.meter("9.0")])
        self.assertIs(self.coordinator.ems_meters, old_meters)
        self.assertEqual(self.client.published, [])

    def test_disconnect_is_idempotent(self):
        self.coordinator.disconnect()
        self.coordinator.disconnect()
        self.assertEqual(self.client.disconnect_calls, 1)
        self.assertEqual(self.client.loop_stop_calls, 1)

    def test_disconnect_failure_still_stops_worker(self):
        def fail_disconnect():
            self.client.disconnect_calls += 1
            raise OSError("broker unreachable")
        self.client.disconnect = fail_disconnect
        self.coordinator.disconnect()
        self.assertIsNone(self.coordinator.client)
        self.assertEqual(self.client.loop_stop_calls, 1)
        self.assertFalse(self.coordinator.connected.is_set())

    def test_queued_callback_is_ignored_after_unload(self):
        self.client.emit([self.geo(), self.meter()])
        self.assertTrue(self.loop.pending)
        self.coordinator.disconnect()
        self.loop.flush()
        self.assertEqual(self.events, [])

    def test_closed_ha_loop_does_not_accept_callbacks(self):
        self.loop.closed = True
        self.client.emit([self.geo(), self.meter()])
        self.assertEqual(self.loop.pending, [])

    def test_stage7_morning_peak_preserves_raw_kw_without_scaling(self):
        # Representative test fixture inspired by the Euros app's morning
        # import spike, NOT a synchronized sample or a sign calibration.
        self.client.emit([self.geo(), self.meter("4.2")])
        raw = self.coordinator.ems_meters["METER_1"]["TOTAL_ACT_POW_FL_1"]
        ems = sys.modules["custom_components.euros_os.ems"]
        self.assertEqual(ems.parse_ems_numeric(raw), 4.2)
        self.assertEqual(self.client.published, [])

    def test_stage7_negative_and_zero_grid_power_remain_distinct(self):
        ems = sys.modules["custom_components.euros_os.ems"]
        for reading, expected in (("-0.35", -0.35), ("0", 0.0), ("+1.25", 1.25)):
            with self.subTest(reading=reading):
                self.client.emit([self.geo(), self.meter(reading)])
                value = self.coordinator.ems_meters["METER_1"]["TOTAL_ACT_POW_FL_1"]
                self.assertEqual(ems.parse_ems_numeric(value), expected)
        # Direction of grid import/export still needs real synchronized data.

    def test_stage7_bad_meter_value_never_becomes_false_zero(self):
        ems = sys.modules["custom_components.euros_os.ems"]
        for value in ("", "NaN", "not a measurement", None, True):
            with self.subTest(value=value):
                self.client.emit([self.geo(), self.meter(value)])
                reading = self.coordinator.ems_meters["METER_1"].get("TOTAL_ACT_POW_FL_1")
                self.assertIsNone(ems.parse_ems_numeric(reading))

    def test_stage7_meter_only_updates_do_not_refresh_stale_pump(self):
        self.client.emit([self.geo(), self.meter("0.15")])
        original_pump = self.coordinator.device
        self.coordinator._last_update = 100.0  # simulated old pump update
        self.client.emit([self.meter("4.2")])
        self.assertIs(self.coordinator.device, original_pump)
        self.assertEqual(self.coordinator._last_update, 100.0)
        self.assertIn("METER_1", self.coordinator._meter_last_update)
        self.assertEqual(self.coordinator.ems_meters["METER_1"]["TOTAL_ACT_POW_FL_1"], "4.2")

    def test_stage7_missing_meter_in_complete_snapshot_does_not_create_zero(self):
        ems = sys.modules["custom_components.euros_os.ems"]
        self.client.emit([self.geo(), self.meter("0.15")])
        self.client.emit([self.geo()])
        self.assertNotIn("METER_1", self.coordinator.ems_meters)
        self.assertIsNone(ems.parse_ems_numeric(
            self.coordinator.ems_meters.get("METER_1", {}).get("TOTAL_ACT_POW_FL_1")
        ))

    def test_stage7_separate_meters_do_not_contaminate_home_meter(self):
        self.client.emit([self.geo(), self.meter("0.2")])
        other = {"Name": "METER_2", "Type": "METER",
                 "Data": {"TOTAL_ACT_POW_FL_1": "3.7"}}
        self.client.emit([other])
        self.assertEqual(self.coordinator.ems_meters["METER_1"]["TOTAL_ACT_POW_FL_1"], "0.2")
        self.assertEqual(self.coordinator.ems_meters["METER_2"]["TOTAL_ACT_POW_FL_1"], "3.7")
        self.assertEqual(self.client.published, [])

    def test_loss_of_mqtt_does_not_clear_snapshot_or_publish(self):
        self.client.emit([self.geo(), self.meter()])
        self.loop.flush()
        before = (self.coordinator.device.copy(), self.coordinator.ems_meters.copy())
        # No further message: last valid state is retained; entity availability
        # is controlled by the existing MQTT_TIMEOUT mechanism.
        self.assertEqual((self.coordinator.device, self.coordinator.ems_meters), before)
        self.assertEqual(self.client.published, [])


if __name__ == "__main__":
    unittest.main()
