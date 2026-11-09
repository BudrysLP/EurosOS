"""
===============================================================================
Euros OS Home Assistant Custom Integration
===============================================================================

File        : coordinator.py
Author      : Patryk "KoPcIu" Kopeć / https://github.com/McKoPcIu/EurosOS
Integration : euros_os
Version     : 0.1.0
Description : Custom integration for EurosEnergy and E-On devices.

===============================================================================
"""

import threading
import time
import json
import logging
import math
import re
import ssl
import paho.mqtt.client as mqtt
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import callback
from .const import MQTT_PORT, MQTT_USER, MQTT_PASSWORD, MQTT_TIMEOUT
from .ems import extract_ems_meters, parse_ems_numeric
from .discovery import find_pump

_LOGGER = logging.getLogger("custom_components.euros_os")

# Temporary, read-only EMS diagnostics. Only documented numeric meter fields
# are logged; credentials, identifiers and raw GEO payloads are never included.
_EMS_METER_FIELDS = frozenset({
    "A_PHA_VOLT_FL_1",
    "B_PHA_VOLT_FL_1",
    "C_PHA_VOLT_FL_1",
    "AB_LINE_VOLT_FL_1",
    "BC_LINE_VOLT_FL_1",
    "CA_LINE_VOLT_FL_1",
    "A_PHA_CUR_FL_1",
    "B_PHA_CUR_FL_1",
    "C_PHA_CUR_FL_1",
    "A_PHA_ACT_POW_FL_1",
    "B_PHA_ACT_POW_FL_1",
    "C_PHA_ACT_POW_FL_1",
    "TOTAL_ACT_POW_FL_1",
    "A_ACT_POW_FL_1",
    "B_ACT_POW_FL_1",
    "C_ACT_POW_FL_1",
    "TOTAL_RACT_POW_FL_1",
    "A_PHA_VIEW_POW_FL_1",
    "B_PHA_VIEW_POW_FL_1",
    "C_PHA_VIEW_POW_FL_1",
    "TOTAL_APPA_POWER_FL_1",
    "A_PHA_POW_FAC_FL_1",
    "B_PHA_POW_FAC_FL_1",
    "C_PHA_POW_FAC_FL_1",
    "TOTAL_POW_FAC_FL_1",
    "FREQUENCY_FL_1",
    "POS_ACT_POW_FL_1",
    "REW_ACT_POW_FL_1",
    "POS_REAC_POW_FL_1",
    "REW_REAC_POW_FL_1",
    "POS_ACT_POW_FACTOR",
    "REV_ACT_POW_FACTOR",
    "TOTAL_ACT_POW_FACTOR",
})
_EMS_METER_LOG_INTERVAL = 30.0  # seconds
_EMS_NO_METER_LOG_INTERVAL = 300.0  # seconds

class EurosOSMQTTCoordinator(DataUpdateCoordinator):

    def __init__(self, ip, topic, pump_name=None, pump_type=None, event_loop=None):
        super().__init__(None, _LOGGER, name="EurosOS")
        self.ip = ip
        self.topic = topic
        self.pump_name = pump_name
        self.pump_type = pump_type
        self._event_loop = event_loop
        self._closed = False
        self.device = {}
        self.ems_meters = {}  # Current read-only METER_N data, separate from GEO.
        self._meter_last_update = {}  # Independent receive time for each meter.
        self.client = None
        self.connected = threading.Event()
        self._last_update = None
        self._listeners = []
        self._last_ems_diagnostic = None
        self._last_ems_meter_present = None
        self._last_ems_power_received = None
        self._reported_stale_pump = False
        self._reported_stale_meters = frozenset()

    # ------------------ Listeners ------------------
    def async_add_listener(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def async_remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    @callback
    def _notify_listeners(self):
        # MQTT callbacks run in a worker thread; HA entity callbacks must run
        # on the Home Assistant event loop, not directly in that worker.
        if self._closed:
            return
        if self._event_loop is not None:
            if self._event_loop.is_closed():
                return
            try:
                self._event_loop.call_soon_threadsafe(self._dispatch_listeners)
            except RuntimeError:
                # HA may close its event loop between is_closed() and queueing.
                _LOGGER.debug("Skipping MQTT update: Home Assistant loop is closed")
        else:
            self._dispatch_listeners()

    @callback
    def _dispatch_listeners(self):
        if self._closed:
            return
        for listener in tuple(self._listeners):
            listener()

    @callback
    def check_stale(self, now=None):
        """Notify HA once when an already-received MQTT snapshot expires.

        A silent broker sends no message, so the scheduled HA watchdog must
        explicitly write unavailable states. Do not erase snapshots, create
        entities, publish commands, or refresh timestamps.
        """
        if self._closed:
            return False
        current = time.time() if now is None else now
        stale_pump = (
            self._last_update is not None
            and current - self._last_update > MQTT_TIMEOUT
        )
        stale_meters = frozenset(
            name for name, timestamp in self._meter_last_update.items()
            if current - timestamp > MQTT_TIMEOUT
        )
        newly_stale = (
            (stale_pump and not self._reported_stale_pump)
            or bool(stale_meters - self._reported_stale_meters)
        )
        self._reported_stale_pump = stale_pump
        self._reported_stale_meters = stale_meters
        if newly_stale:
            self._notify_listeners()
        return newly_stale

    # ------------------ Read-only EMS diagnostics ------------------
    def _log_ems_diagnostics(self, devices):
        """Low-volume debug counters, without device names or measurements."""
        if not _LOGGER.isEnabledFor(logging.DEBUG) or not isinstance(devices, list):
            return
        now = time.monotonic()
        if (
            self._last_ems_diagnostic is not None
            and now - self._last_ems_diagnostic < _EMS_NO_METER_LOG_INTERVAL
        ):
            return
        self._last_ems_diagnostic = now
        meter_count = sum(
            isinstance(item, dict)
            and isinstance(item.get("Type"), str)
            and item["Type"].upper() == "METER"
            for item in devices
        )
        _LOGGER.debug(
            "[EMS_DIAG] device_count=%d meter_count=%d",
            len(devices), meter_count,
        )

    def _log_ems_power_sample(self, meters, received_at, received_monotonic):
        """Log each valid METER_1 power sample only when DEBUG is enabled.

        Times represent MQTT reception, not the physical meter sampling time.
        Never log the complete payload, credentials, or device identifiers.
        """
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            return
        reading = meters.get("METER_1")
        if not isinstance(reading, dict):
            return
        power_kw = parse_ems_numeric(reading.get("TOTAL_ACT_POW_FL_1"))
        if power_kw is None:
            return
        elapsed = (
            None if self._last_ems_power_received is None
            else round(received_monotonic - self._last_ems_power_received, 3)
        )
        self._last_ems_power_received = received_monotonic
        _LOGGER.debug(
            "[EMS_POWER_SAMPLE] received_unix=%.3f power_kw=%.6f "
            "power_w=%.3f delta_receive_s=%s",
            received_at, power_kw, power_kw * 1000,
            elapsed if elapsed is not None else "first",
        )

    # ------------------ MQTT ------------------
    def disconnect(self):
        """Stop the MQTT worker when the HA config entry is unloaded.

        Do not delete device snapshots or HA entity registry entries.
        """
        self._closed = True
        client = self.client
        self.client = None
        self.connected.clear()
        if client is None:
            return
        try:
            client.disconnect()
        except Exception as exc:
            # A broker/socket failure must not block unloading the HA entry.
            _LOGGER.warning("MQTT disconnect failed: %s", exc)
        finally:
            try:
                client.loop_stop()
            except Exception as exc:
                _LOGGER.warning("MQTT worker shutdown failed: %s", exc)

    def connect(self):
        self._closed = False
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                _LOGGER.debug("Connected to MQTT broker at %s", self.ip)
                client.subscribe(self.topic)
                self.connected.set()
            else:
                _LOGGER.error("Failed to connect to MQTT broker, rc=%s", rc)

        def on_disconnect(client, userdata, rc, *args):
            self.connected.clear()
            if not self._closed and rc != 0:
                _LOGGER.warning("MQTT connection lost (rc=%s); retaining last valid readings", rc)

        def on_message(client, userdata, msg):
            if self._closed:
                return
            try:
                payload = json.loads(msg.payload)
                if not isinstance(payload, dict):
                    return
                devices = payload.get("Devices")
                if not isinstance(devices, list) or not devices:
                    return

                self._log_ems_diagnostics(devices)
                received_at = time.time()
                received_monotonic = time.monotonic()
                pump = find_pump(
                    devices, expected_name=self.pump_name, expected_type=self.pump_type
                )
                meters = extract_ems_meters(devices)

                if pump is None:
                    # Only accept packets made entirely of METER devices.
                    # Another/ambiguous/unknown pump must never masquerade
                    # as a meter-only update to this configured entry.
                    meter_only = all(
                        isinstance(device, dict)
                        and isinstance(device.get("Type"), str)
                        and device["Type"].upper() == "METER"
                        for device in devices
                    )
                    if not meter_only or not meters:
                        _LOGGER.debug("Ignoring MQTT packet without configured pump or usable meters")
                        return

                    # A meter-only update must not refresh pump freshness.
                    # Replace mapping snapshots atomically: HA may iterate
                    # the old mappings on its event loop simultaneously.
                    self.ems_meters = {**self.ems_meters, **meters}
                    self._meter_last_update = {
                        **self._meter_last_update,
                        **{name: received_at for name in meters},
                    }
                else:
                    # Pump-containing /Dev payload is a complete snapshot.
                    # Missing meters become unavailable but registered HA
                    # entities and their history are never deleted.
                    self.device = pump
                    self._last_update = received_at
                    self.ems_meters = meters
                    self._meter_last_update = {
                        name: received_at for name in meters
                    }
                    _LOGGER.debug("Received MQTT pump telemetry")

                self._notify_listeners()
            except Exception as e:
                _LOGGER.warning("Ignoring malformed MQTT telemetry (%s)", type(e).__name__)

        client = mqtt.Client()
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        client.tls_set_context(ssl._create_unverified_context())

        self.client = client
        try:
            client.connect(self.ip, MQTT_PORT, 60)
            client.loop_start()
            if not self.connected.wait(timeout=5.0):
                raise ConnectionError("MQTT connection acknowledgement timed out")
        except Exception as exc:
            # A failed setup must not leave a running Paho worker. HA can
            # retry the config entry when the broker is reachable again.
            self.disconnect()
            raise ConnectionError("Euros OS MQTT connection unavailable") from exc

    # ------------------ DataSending ------------------
    async def async_set_device_value(self, data: dict, entry_data: dict = None):
        if not self.client or not self.connected.is_set():
            _LOGGER.warning("MQTT command rejected: connection is unavailable")
            return False

        device_name = entry_data.get("device_model") if entry_data else None
        device_type = entry_data.get("device_type") if entry_data else None
        device_version = entry_data.get("device_version") if entry_data else None

        if not all([device_name, device_type, device_version]):
            _LOGGER.error("Cannot publish: incomplete device information")
            return False

        payload = json.dumps({
            "Devices": [
                {
                    "Name": device_name,
                    "Data": data,
                    "Type": device_type,
                    "Version": device_version
                }
            ]
        })

        topic = self.topic.replace("/Dev", "") + "/App"
        _LOGGER.debug("Publishing Euros OS device command")
        try:
            published = self.client.publish(topic, payload, retain=False)
        except Exception as exc:
            _LOGGER.warning("MQTT command publish failed (%s)", type(exc).__name__)
            return False
        if getattr(published, "rc", None) != mqtt.MQTT_ERR_SUCCESS:
            _LOGGER.warning("MQTT command was not accepted by the client")
            return False
        # Accepted for sending is not confirmation that the pump applied it.
        return True

    # ------------------ DataUpdateCoordinator ------------------
    async def _async_update_data(self):
        return self.device
