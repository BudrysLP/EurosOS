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
        self.emit_raw(json.dumps({"Devices": devices}).encode())

    def emit_raw(self, payload):
        self.on_message(self, None, types.SimpleNamespace(payload=payload))

    def simulate_disconnect(self, rc=7):
        self.on_disconnect(self, None, rc)

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

    def test_broken_json_and_unexpected_payload_types_are_ignored(self):
        self.client.emit([self.geo(), self.meter()])
        self.loop.flush()
        snapshot = (self.coordinator.device, self.coordinator.ems_meters,
                    self.coordinator._last_update, self.coordinator._meter_last_update)
        for invalid in (
            b"{malformed",
            b"null",
            b"[]",
            b'"hello"',
            b'{"Devices":"not a list"}',
            b'{"Devices":[]}',
            b'{"WrongField":[]}',
        ):
            with self.subTest(invalid=invalid):
                self.client.emit_raw(invalid)
                self.assertEqual(
                    (self.coordinator.device, self.coordinator.ems_meters,
                     self.coordinator._last_update, self.coordinator._meter_last_update),
                    snapshot,
                )
        self.assertEqual(self.loop.pending, [])
        self.assertEqual(self.client.published, [])

    def test_malformed_pump_packet_cannot_update_attached_meter(self):
        self.client.emit([self.geo(), self.meter()])
        before = self.coordinator.ems_meters
        invalid_pump = {"Name": "GEO_1", "Type": "FriskoGEO", "Data": None}
        self.client.emit([invalid_pump, self.meter("999")])
        self.assertIs(self.coordinator.ems_meters, before)
        self.assertEqual(self.coordinator.ems_meters["METER_1"]["TOTAL_ACT_POW_FL_1"], "0.168")

    def test_ambiguous_duplicate_pump_is_rejected(self):
        self.client.emit([self.geo(), self.meter()])
        before = self.coordinator.ems_meters
        self.client.emit([self.geo(), self.geo(), self.meter("999")])
        self.assertIs(self.coordinator.ems_meters, before)

    def test_multiple_meter_partial_refresh_preserves_other_meters(self):
        meter2 = {"Name": "METER_2", "Type": "METER",
                  "Data": {"TOTAL_ACT_POW_FL_1": "0.023"}}
        self.client.emit([meter2, self.geo(), self.meter()])
        old_pump_time = self.coordinator._last_update
        old_meter1 = self.coordinator._meter_last_update["METER_1"]
        meter3 = {"Name": "METER_3", "Type": "METER",
                  "Data": {"TOTAL_ACT_POW_FL_1": "-0.11"}}
        self.client.emit([meter3, meter2])
        self.assertEqual(self.coordinator._last_update, old_pump_time)
        self.assertEqual(self.coordinator._meter_last_update["METER_1"], old_meter1)
        self.assertEqual(set(self.coordinator.ems_meters), {"METER_1", "METER_2", "METER_3"})
        self.assertEqual(self.coordinator.ems_meters["METER_3"]["TOTAL_ACT_POW_FL_1"], "-0.11")
        self.assertEqual(self.client.published, [])

    def test_duplicate_meter_packet_is_not_last_wins(self):
        self.client.emit([self.geo(), self.meter()])
        self.client.emit([self.geo(), self.meter("0.1"), self.meter("1000")])
        self.assertNotIn("METER_1", self.coordinator.ems_meters)
        self.assertNotIn("METER_1", self.coordinator._meter_last_update)

    def test_network_disconnect_then_reconnect_preserves_state(self):
        self.client.emit([self.geo(), self.meter()])
        self.client.simulate_disconnect(rc=7)
        self.assertFalse(self.coordinator.connected.is_set())
        self.assertEqual(self.coordinator.device["Name"], "GEO_1")
        self.assertIn("METER_1", self.coordinator.ems_meters)
        self.client.on_connect(self.client, None, None, 0)
        self.assertTrue(self.coordinator.connected.is_set())
        self.client.emit([self.geo(), self.meter("0.25")])
        self.assertEqual(self.coordinator.ems_meters["METER_1"]["TOTAL_ACT_POW_FL_1"], "0.25")

    def test_closed_loop_race_does_not_crash_mqtt_thread(self):
        def closed_between_check_and_schedule(*args):
            raise RuntimeError("Event loop is closed")
        self.loop.call_soon_threadsafe = closed_between_check_and_schedule
        self.client.emit([self.geo(), self.meter()])
        self.assertEqual(self.coordinator.device["Name"], "GEO_1")
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
