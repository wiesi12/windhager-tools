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
}


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

    except Exception:

        return False