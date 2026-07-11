from __future__ import annotations

from typing import Final


UnitDefinition = tuple[str, float, float]


UNIT_DEFINITIONS: Final[dict[str, UnitDefinition]] = {
    "1": ("fraction", 1.0, 0.0),
    "fraction": ("fraction", 1.0, 0.0),
    "%": ("fraction", 0.01, 0.0),
    "count": ("count", 1.0, 0.0),
    "counts": ("count", 1.0, 0.0),
    "particles": ("count", 1.0, 0.0),
    "category": ("category", 1.0, 0.0),
    "W": ("power", 1.0, 0.0),
    "kW": ("power", 1_000.0, 0.0),
    "kWt": ("power", 1_000.0, 0.0),
    "MW": ("power", 1_000_000.0, 0.0),
    "g/s": ("mass_flow", 0.001, 0.0),
    "kg/s": ("mass_flow", 1.0, 0.0),
    "Pa": ("pressure", 1.0, 0.0),
    "kPa": ("pressure", 1_000.0, 0.0),
    "MPa": ("pressure", 1_000_000.0, 0.0),
    "K": ("temperature", 1.0, 0.0),
    "degC": ("temperature", 1.0, 273.15),
    "°C": ("temperature", 1.0, 273.15),
    "s": ("time", 1.0, 0.0),
    "min": ("time", 60.0, 0.0),
    "h": ("time", 3_600.0, 0.0),
}


def can_convert_units(*, from_units: str, to_units: str) -> bool:
    if from_units not in UNIT_DEFINITIONS or to_units not in UNIT_DEFINITIONS:
        return False
    from_dimension, _, _ = UNIT_DEFINITIONS[from_units]
    to_dimension, _, _ = UNIT_DEFINITIONS[to_units]
    if from_dimension == "temperature" or to_dimension == "temperature":
        return from_units == to_units
    return from_dimension == to_dimension


def convert_value(*, value: float, from_units: str, to_units: str) -> float:
    if not can_convert_units(from_units=from_units, to_units=to_units):
        raise ValueError(f"cannot convert {from_units!r} to {to_units!r}")
    _, from_scale, from_offset = UNIT_DEFINITIONS[from_units]
    _, to_scale, to_offset = UNIT_DEFINITIONS[to_units]
    base_value = value * from_scale + from_offset
    return (base_value - to_offset) / to_scale
