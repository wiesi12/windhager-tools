"""Gemeinsames Test-Setup fuer pytest.

Macht "lib" als eigenstaendiges, importierbares Paket verfuegbar
(z.B. "from lib.models import Module"), unabhaengig von der
custom_components-Verzeichnisstruktur, die nur innerhalb einer
echten Home-Assistant-Installation aufgeloest wird.

Tests fuer reinen, Home-Assistant-unabhaengigen Code (lib/) brauchen
dadurch kein installiertes Home Assistant, um zu laufen - nur die
Standardbibliothek + die hier getesteten Module selbst.

Zusaetzlich: ein minimaler Mock fuer die paar "homeassistant"-Symbole,
die metadata.py tatsaechlich braucht (SensorDeviceClass,
SensorStateClass, EntityCategory) - das vollwertige "homeassistant"-
Paket waere ein unnoetig schwergewichtiges Test-Dependency nur fuer
ein paar Enum-Konstanten. Wird VOR jedem Test-Modul-Import registriert,
damit "from homeassistant.components.sensor import ..." in
metadata.py funktioniert, ohne dass Home Assistant selbst installiert
sein muss.
"""

import sys
import types
from pathlib import Path


INTEGRATION_DIR = (
    Path(__file__).parent.parent
    / "custom_components"
    / "windhager_infowin"
)

sys.path.insert(
    0,
    str(INTEGRATION_DIR),
)


def _install_homeassistant_mock():

    if "homeassistant" in sys.modules:

        # Echtes (oder bereits gemocktes) homeassistant ist schon da -
        # nicht ueberschreiben, falls der Test-Lauf z.B. zusaetzlich
        # gegen ein echtes Home-Assistant-Environment laufen soll.
        return

    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType(
        "homeassistant.components"
    )
    sensor = types.ModuleType(
        "homeassistant.components.sensor"
    )
    const = types.ModuleType("homeassistant.const")

    class SensorDeviceClass:
        TEMPERATURE = "temperature"
        PRESSURE = "pressure"
        VOLTAGE = "voltage"
        CURRENT = "current"
        FREQUENCY = "frequency"
        POWER = "power"
        ENERGY = "energy"
        WEIGHT = "weight"
        DURATION = "duration"
        DATE = "date"
        ENUM = "enum"
        GAS = "gas"
        MONETARY = "monetary"
        TIMESTAMP = "timestamp"
        VOLUME = "volume"
        WATER = "water"

    class SensorStateClass:
        MEASUREMENT = "measurement"
        TOTAL = "total"
        TOTAL_INCREASING = "total_increasing"

    class EntityCategory:
        DIAGNOSTIC = "diagnostic"

    sensor.SensorDeviceClass = SensorDeviceClass
    sensor.SensorStateClass = SensorStateClass
    const.EntityCategory = EntityCategory

    sys.modules["homeassistant"] = homeassistant
    sys.modules[
        "homeassistant.components"
    ] = components
    sys.modules[
        "homeassistant.components.sensor"
    ] = sensor
    sys.modules["homeassistant.const"] = const


_install_homeassistant_mock()

