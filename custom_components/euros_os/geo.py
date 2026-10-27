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
}

GEO_GROUND_SOURCE_DELTA_T = "GEO_GROUND_SOURCE_DELTA_T"
GEO_GROUND_SOURCE_DELTA_T_NAME = "Temperatura różnicowa dolnego źródła (ΔT)"


def sensor_info_for_device(key: str, info: tuple, device_type: str | None) -> tuple:
    """Override only GEO labels, retaining units, icons and other metadata."""
    if device_type != GEO_DEVICE_TYPE:
        return info
    label = GEO_SENSOR_NAME_OVERRIDES.get(key)
    return (label, *info[1:]) if label else info


def calculate_ground_source_delta_t(data: Mapping[str, object]) -> float | None:
    """T3fiz (return from ground) - T4fiz (outlet to ground), in °C.

    None means that at least one measurement is absent, invalid or outside
    the same plausible temperature bounds used by the existing integration.
    """
    try:
        return_temp = float(data["T3fiz"])
        outlet_temp = float(data["T4fiz"])
    except (KeyError, TypeError, ValueError):
        return None

    if not (math.isfinite(return_temp) and math.isfinite(outlet_temp)):
        return None
    if not (-50 <= return_temp <= 149 and -50 <= outlet_temp <= 149):
        return None

    return round(return_temp - outlet_temp, 1)
