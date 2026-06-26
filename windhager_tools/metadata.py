from homeassistant.components.sensor import (
    SensorDeviceClass,
)
from homeassistant.const import (
    EntityCategory,
)


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


PRECISION = {
    "°C": 1,
    "%": 0,
}


DIAGNOSTIC_LOOKUPS = {
    "Modulinfo",
}


def device_class(entry):

    return DEVICE_CLASSES.get(
        entry.unit
    )


def precision(entry):

    return PRECISION.get(
        entry.unit
    )


def entity_category(
    lookup,
):

    if lookup.name in DIAGNOSTIC_LOOKUPS:

        return EntityCategory.DIAGNOSTIC

    return None


def is_numeric(entry):

    try:

        float(
            str(entry.value).replace(
                ",",
                ".",
            )
        )

        return True

    except Exception:

        return False