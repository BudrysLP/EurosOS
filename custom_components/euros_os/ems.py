"""Read-only helpers for Euros EMS meter telemetry on the existing /Dev MQTT topic.

METER_1 is the electricity meter for the whole home's grid connection,
NOT a dedicated meter for the Euros heat pump. Future METER_2/METER_3
can be supported without changing these identifiers.
"""

import math
import re

EMS_DOM_METER_NAME = "METER_1"
EMS_DOM_DEVICE_NAME = "EMS – Dom"

# key: (name, unit, icon, sensor device class, state class)
# Values from /Dev METER_1 are already scaled to these units.
EMS_DOM_SENSOR_DEFINITIONS = {
    "TOTAL_ACT_POW_FL_1": ("EMS – Dom – Bilans mocy chwilowej", "kW", "mdi:transmission-tower", "power", "measurement"),
    "POS_ACT_POW_FL_1": ("EMS – Dom – Energia pobrana z sieci", "kWh", "mdi:transmission-tower-import", "energy", "total_increasing"),
    "REW_ACT_POW_FL_1": ("EMS – Dom – Energia oddana do sieci", "kWh", "mdi:transmission-tower-export", "energy", "total_increasing"),
    "A_PHA_VOLT_FL_1": ("EMS – Dom – Napięcie L1", "V", "mdi:flash", "voltage", "measurement"),
    "B_PHA_VOLT_FL_1": ("EMS – Dom – Napięcie L2", "V", "mdi:flash", "voltage", "measurement"),
    "C_PHA_VOLT_FL_1": ("EMS – Dom – Napięcie L3", "V", "mdi:flash", "voltage", "measurement"),
    "A_PHA_CUR_FL_1": ("EMS – Dom – Prąd L1", "A", "mdi:current-ac", "current", "measurement"),
    "B_PHA_CUR_FL_1": ("EMS – Dom – Prąd L2", "A", "mdi:current-ac", "current", "measurement"),
    "C_PHA_CUR_FL_1": ("EMS – Dom – Prąd L3", "A", "mdi:current-ac", "current", "measurement"),
    "FREQUENCY_FL_1": ("EMS – Dom – Częstotliwość sieci", "Hz", "mdi:sine-wave", "frequency", "measurement"),
}


def extract_ems_meters(devices):
    """Return current METER_N -> Data mappings; ignore the pump and unknown devices.

    Only devices explicitly tagged Type=METER are accepted. No messages are
    published or new MQTT topics subscribed to.
    """
    if not isinstance(devices, list):
        return {}

    meters = {}
    for device in devices:
        if not isinstance(device, dict):
            continue
        name = device.get("Name")
        meter_type = device.get("Type")
        data = device.get("Data")
        if (
            isinstance(name, str)
            and re.fullmatch(r"METER_[1-9][0-9]*", name, re.IGNORECASE)
            and isinstance(meter_type, str)
            and meter_type.upper() == "METER"
            and isinstance(data, dict)
        ):
            meters[name.upper()] = data
    return meters


def parse_ems_numeric(value):
    """Return a finite numeric reading, or None if the field is absent/invalid.

    Zero is only returned when the meter *actually* reports zero.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None
