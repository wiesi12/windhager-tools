from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import EntityCategory


DIAGNOSTIC_LOOKUPS = {
    "Modulinfo",
}


DEVICE_CLASSES = {
    "°C": SensorDeviceClass.TEMPERATURE,
    "K": SensorDeviceClass.TEMPERATURE,
    "bar": SensorDeviceClass.PRESSURE,
    "V": SensorDeviceClass.VOLTAGE,
    "A": SensorDeviceClass.CURRENT,
    "Hz": SensorDeviceClass.FREQUENCY,
    "W": SensorDeviceClass.POWER,
    "kW": SensorDeviceClass.POWER,
    "Wh": SensorDeviceClass.ENERGY,
    "kWh": SensorDeviceClass.ENERGY,
    "kg": SensorDeviceClass.WEIGHT,
    "Std": SensorDeviceClass.DURATION,
}


def classify(entry, lookup=None):

    if lookup and lookup.name in DIAGNOSTIC_LOOKUPS:
        return "diagnostic"

    unit = entry.unit

    if unit in ("°C", "K"):
        return "temperature"

    if unit == "%":
        return "percentage"

    if unit == "bar":
        return "pressure"

    if unit in ("W", "kW"):
        return "power"

    if unit in ("Wh", "kWh"):
        return "energy"

    if unit == "V":
        return "voltage"

    if unit == "A":
        return "current"

    if unit == "Hz":
        return "frequency"

    if unit == "min":
        return "duration"

    if unit == "Std":
        return "duration"

    if unit == "kg":
        return "weight"

    if unit == "rpm":
        return "frequency"

    if unit == "d":
        return "days"

    if unit == "20":
        return "date"

    if unit == "21":
        return "time"

    # NvEntry hat kein write_protected-Attribut (NV's sind grundsaetzlich
    # nur lesbare Mess-/Statuswerte, daher "sensor" als Default).
    if getattr(entry, "write_protected", True):
        return "sensor"

    return "setting"


def device_class(entry):

    return DEVICE_CLASSES.get(entry.unit)


def entity_category(lookup):

    if lookup.name in DIAGNOSTIC_LOOKUPS:
        return EntityCategory.DIAGNOSTIC

    return None


def suggested_precision(entry):

    if entry.unit == "°C":
        return 1

    if entry.unit == "%":
        return 0

    return None


def has_numeric_value(entry):

    if entry.unit is None:
        return False

    try:

        float(
            str(entry.value).replace(",", ".")
        )

        return True

    except (ValueError, TypeError):

        # z.B. NV-Werte, die noch nicht gepollt wurden ("-"),
        # oder nicht-numerische Statuswerte.
        return False


def icon(entry, lookup=None):

    kind = classify(entry, lookup)

    icons = {
        "temperature": "mdi:thermometer",
        "pressure": "mdi:gauge",
        "power": "mdi:flash",
        "energy": "mdi:lightning-bolt",
        "voltage": "mdi:sine-wave",
        "current": "mdi:current-ac",
        "frequency": "mdi:pulse",
        "duration": "mdi:timer-outline",
        "date": "mdi:calendar",
        "time": "mdi:clock-outline",
        "percentage": "mdi:percent",
        "weight": "mdi:weight-kilogram",
        "diagnostic": "mdi:information-outline",
        "setting": "mdi:cog-outline",
        "sensor": "mdi:chart-line",
    }

    return icons.get(kind)


def metadata(entry, lookup=None):

    return {
        "classification": classify(entry, lookup),
        "device_class": device_class(entry),
        "entity_category": entity_category(lookup) if lookup else None,
        "precision": suggested_precision(entry),
        "icon": icon(entry, lookup),
        "numeric": has_numeric_value(entry),
    }