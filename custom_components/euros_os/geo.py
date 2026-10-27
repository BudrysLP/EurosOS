"""Model-specific helpers for Euros GEO heat pumps.

The source returns to the heat pump through T3fiz and the pump sends the
cooled fluid back to the ground through T4fiz. Both assignments have been
confirmed for FriskoGEO; other device types keep their original labels.
"""

import math
from collections.abc import Mapping

GEO_DEVICE_TYPE = "FriskoGEO"

GEO_SENSOR_NAME_OVERRIDES = {
    "T3fiz": "Temperatura powrotu z dolnego źródła",
    "T4fiz": "Temperatura wyjścia do dolnego źródła",
    "T5fiz": "Górne źródło — temperatura powrotu",
    "TSM13": "Górne źródło — temperatura zasilania",
}

GEO_GROUND_SOURCE_DELTA_T = "GEO_GROUND_SOURCE_DELTA_T"
GEO_GROUND_SOURCE_DELTA_T_NAME = "Temperatura różnicowa dolnego źródła (ΔT)"

GEO_UPPER_SOURCE_DELTA_T = "GEO_UPPER_SOURCE_DELTA_T"
GEO_UPPER_SOURCE_DELTA_T_NAME = "Górne źródło — temperatura różnicowa (ΔT)"


def sensor_info_for_device(key: str, info: tuple, device_type: str | None) -> tuple:
    """Override only GEO labels, retaining units, icons and other metadata."""
    if device_type != GEO_DEVICE_TYPE:
        return info
    label = GEO_SENSOR_NAME_OVERRIDES.get(key)
    return (label, *info[1:]) if label else info


def _calculate_delta_t(
    data: Mapping[str, object], warm_sensor: str, cool_sensor: str
) -> float | None:
    """Calculate a temperature difference without treating absent values as zero."""
    try:
        warm_temp = float(data[warm_sensor])
        cool_temp = float(data[cool_sensor])
    except (KeyError, TypeError, ValueError):
        return None

    if not (math.isfinite(warm_temp) and math.isfinite(cool_temp)):
        return None
    if not (-50 <= warm_temp <= 149 and -50 <= cool_temp <= 149):
        return None

    return round(warm_temp - cool_temp, 1)


def calculate_ground_source_delta_t(data: Mapping[str, object]) -> float | None:
    """Return from ground (T3fiz) minus outlet to ground (T4fiz), in °C."""
    return _calculate_delta_t(data, "T3fiz", "T4fiz")


def calculate_upper_source_delta_t(data: Mapping[str, object]) -> float | None:
    """Heating-side supply (TSM13) minus return (T5fiz), in °C."""
    return _calculate_delta_t(data, "TSM13", "T5fiz")
