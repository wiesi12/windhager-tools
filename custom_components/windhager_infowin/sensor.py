from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import metadata
from . import naming
from .lib.slug import build_slug
from .pmx_state_translation import translate_pmx_state


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
):

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    nv_coordinator = hass.data[DOMAIN][entry.entry_id]["nv_coordinator"]
    system = hass.data[DOMAIN][entry.entry_id]["system"]

    entities = [
        WindhagerSensor(
            # NV-Entities (Schluessel "nv:...") werden beim
            # nv_coordinator registriert, damit sie bei dessen
            # selteneren Updates (Standard: alle 10 Minuten) neu
            # geschrieben werden. Alle anderen (normale OID-Sensoren)
            # bleiben am haeufigen 30s-coordinator.
            nv_coordinator if oid.startswith("nv:") else coordinator,
            system,
            oid,
        )
        for oid in coordinator.data
        # Schreibbare normale OID-Entries landen als number/select
        # Entity (nicht als read-only Sensor) - kein Duplikat.
        # NV-Entries haben kein write_protected-Attribut und landen
        # immer als Sensor.
        #
        # AUSNAHME: Entries mit write_protected: false aber
        # min_value == max_value (z.B. "Raumtemperatur Aktueller Wert"
        # mit min=max=0.0) sind konzeptuell Messwerte - sie landen
        # als Sensor, nicht als number.
        if oid.startswith("nv:")
        or system.oid_map.get(oid, {}).get("entry") is None
        or getattr(
            system.oid_map[oid]["entry"],
            "write_protected",
            True,
        )
        or (
            not getattr(
                system.oid_map[oid]["entry"],
                "enum",
                None,
            )
            and system.oid_map[oid]["entry"].min_value is not None
            and system.oid_map[oid]["entry"].max_value is not None
            and system.oid_map[oid]["entry"].min_value
            == system.oid_map[oid]["entry"].max_value
        )
        or (
            not getattr(
                system.oid_map[oid]["entry"],
                "enum",
                None,
            )
            and not getattr(
                system.oid_map[oid]["entry"],
                "write_protected",
                True,
            )
            and system.oid_map[oid]["entry"].min_value is not None
            and system.oid_map[oid]["entry"].max_value is not None
            and system.oid_map[oid]["entry"].min_value
            != system.oid_map[oid]["entry"].max_value
            and getattr(
                system.oid_map[oid]["entry"],
                "unit_id",
                None,
            ) in (0, 20, 21)
        )
    ]

    # PMX-Brennerzustand-Sensor nur anlegen wenn NV-Index 27 auf
    # Modul 60 tatsaechlich in der Anlage vorhanden ist.
    if "nv:60:27" in system.oid_map:
        entities.append(
            WindhagerPmxStateSensor(nv_coordinator, system)
        )

    # Pellet-Foerdermenge-Sensor nur anlegen wenn NV-Index 19 auf
    # Modul 60 tatsaechlich vorhanden ist.
    if "nv:60:19" in system.oid_map:
        entities.append(
            WindhagerPelletSensor(nv_coordinator, system, entry)
        )

    async_add_entities(entities)


class WindhagerPmxStateSensor(
    CoordinatorEntity,
    SensorEntity,
):
    """Sensor fuer den PMX-Brennerzustand (NV-Index 27).

    Liefert einen lesbaren Zustandsnamen statt des rohen Hex-Werts.
    Unbekannte Zustaende (z.B. andere Firmware-Versionen) werden als
    Rohwert durchgereicht (known_state=False) statt einen Fehler zu
    werfen, damit Nutzer anderer Anlagen trotzdem Daten sammeln koennen.

    Verifikation: BioWIN 2 Touch, PMX-Controller, 5 Tage / 17 Zyklen.
    Details: pmx_state_translation.py
    """

    _attr_has_entity_name = True
    _attr_name = "PMX Brennerzustand"
    _attr_icon = "mdi:fire"

    def __init__(self, coordinator, system):
        super().__init__(coordinator)
        self.system = system

    @property
    def unique_id(self):
        return "windhager_v2_pmx_state_zustand"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, "module2_60")},
            manufacturer="Windhager",
            model="InfoWIN",
        )

    @property
    def _raw_hex(self) -> int | None:
        if self.coordinator.data is None:
            # NV-Coordinator noch nicht bereit (Hintergrund-Refresh
            # nach dem Start noch nicht abgeschlossen). Letzten
            # bekannten Wert aus dem HA-State-Cache lesen, damit der
            # Sensor nach einem Neustart nicht "Unbekannt" zeigt bis
            # der erste Refresh durch ist (~25s).
            # Das "raw"-Attribut (z.B. "0x0100") das wir selbst
            # mitliefern dient hier als zuverlaessige Quelle - es
            # enthaelt immer den letzten echten Hex-Wert.
            try:
                last_state = self.hass.states.get(self.entity_id)
                if last_state and last_state.state not in (
                    "unknown", "unavailable", None
                ):
                    raw_attr = last_state.attributes.get("raw", "")
                    return int(str(raw_attr), 16)
            except (ValueError, TypeError, AttributeError):
                pass
            return None
        raw = self.coordinator.data.get("nv:60:27")
        if raw is None or raw == "-":
            return None
        # NV-Coordinator liefert den Wert als Entry-Objekt mit .value
        value = raw.value if hasattr(raw, "value") else raw
        try:
            return int(str(value), 16)
        except (ValueError, TypeError):
            return None

    @property
    def native_value(self) -> str | None:
        raw = self._raw_hex
        if raw is None:
            return None
        return translate_pmx_state(raw)["label"]

    @property
    def extra_state_attributes(self) -> dict:
        raw = self._raw_hex
        if raw is None:
            return {}
        info = translate_pmx_state(raw)
        return {
            "phase":       info["phase"],
            "active":      info["active"],
            "confidence":  info["confidence"],
            "known_state": info["known_state"],
            "raw":         info["raw"],
        }


class WindhagerPelletSensor(
    CoordinatorEntity,
    SensorEntity,
):
    """Sensor fuer die Pellet-Foerdermenge Summe (NV-Index 19)
    mit konfigurierbarem Einheitenfaktor.

    Der Rohwert des NV-Sensors ist anlagenabhaengig - auf der
    BioWIN 2 Touch entspricht 1 Roheinheit 10 kg (d.h. Faktor 10,
    10.206 Roheinheiten = 102.06 t). Auf anderen Anlagen kann der
    Faktor abweichen. Der Faktor wird im Options Flow konfiguriert
    (Standard: 1.0 = kein Umrechnen).

    Ergebnis-Einheit: Tonnen (t) wenn Faktor > 1, sonst Roheinheit.
    """

    _attr_has_entity_name = True
    _attr_name = "Pellet Foerdermenge Gesamt"
    _attr_icon = "mdi:silo"
    _attr_state_class = "total_increasing"
    _attr_native_unit_of_measurement = "t"

    def __init__(self, coordinator, system, entry):
        super().__init__(coordinator)
        self.system = system
        self._entry = entry

    @property
    def unique_id(self):
        return "windhager_v2_pellet_foerdermenge_gesamt"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, "module2_60")},
            manufacturer="Windhager",
            model="InfoWIN",
        )

    @property
    def _factor(self) -> float:
        return float(
            self._entry.data.get("pellet_unit_factor", 1.0)
        )

    @property
    def _raw_value(self) -> float | None:
        if self.coordinator.data is None:
            try:
                last_state = self.hass.states.get(
                    self.entity_id
                )
                if last_state and last_state.state not in (
                    "unknown", "unavailable", None,
                ):
                    return float(last_state.state) / self._factor * self._factor
            except (ValueError, TypeError, AttributeError):
                pass
            return None
        raw = self.coordinator.data.get("nv:60:19")
        if raw is None or raw == "-":
            return None
        value = raw.value if hasattr(raw, "value") else raw
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return None

    @property
    def native_value(self) -> float | None:
        raw = self._raw_value
        if raw is None:
            return None
        factor = self._factor
        result = raw * factor / 1000
        return round(result, 3)

    @property
    def extra_state_attributes(self) -> dict:
        raw = self._raw_value
        if raw is None:
            return {}
        return {
            "raw": raw,
            "unit_factor": self._factor,
        }


class WindhagerSensor(
    CoordinatorEntity,
    SensorEntity,
):

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        system,
        oid,
    ):

        super().__init__(coordinator)

        self.system = system
        self.oid = oid

    @property
    def info(self):

        return self.system.oid_map.get(
            self.oid
        )

    @property
    def live_entry(self):
        """Den aktuellen Live-Entry aus dem Coordinator sicher
        abrufen. self.coordinator.data ist None, bis der Coordinator
        seinen ersten Refresh abgeschlossen hat - das passiert beim
        nv_coordinator bewusst NICHT blockierend waehrend des
        Integrations-Setups (siehe __init__.py), daher koennen
        Entities kurzzeitig erzeugt werden, bevor echte Daten
        vorliegen.

        Fallback: wenn noch keine Coordinator-Daten vorliegen, den
        letzten bekannten HA-State aus der Registry lesen - damit
        zeigen Sensoren nach einem Neustart sofort ihren letzten Wert
        statt "-" / "Unbekannt", bis der erste Refresh abgeschlossen
        ist. Gibt None zurueck wenn auch kein letzter State bekannt.
        """

        if self.coordinator.data is not None:
            return self.coordinator.data.get(self.oid)

        # Coordinator noch nicht bereit - letzten bekannten State
        # aus HA lesen. Wir bauen ein minimales Entry-aehnliches
        # Objekt das nur .value hat, damit der Rest der Property-
        # Kette (native_value, meta, etc.) unveraendert funktioniert.
        try:
            last_state = self.hass.states.get(self.entity_id)
            if last_state and last_state.state not in (
                "unknown", "unavailable", None, "-",
            ):
                # Minimales Stub-Objekt mit .value und .unit
                entry = self.entry
                unit = (
                    last_state.attributes.get(
                        "unit_of_measurement", ""
                    )
                    if entry is None
                    else getattr(entry, "unit", "")
                )

                class _StubEntry:
                    def __init__(self, value, unit):
                        self.value = value
                        self.unit = unit

                return _StubEntry(last_state.state, unit)
        except (AttributeError, Exception):
            pass

        return None

    @property
    def entry(self):

        if self.info is None:
            return None

        return self.info["entry"]

    @property
    def lookup(self):

        if self.info is None:
            return None

        return self.info["lookup"]

    @property
    def meta(self):

        if self.entry is None:
            return {}

        # WICHTIG: self.entry kommt aus dem statischen Katalog
        # (system.oid_map) und enthaelt bei NV's immer den
        # Platzhalterwert "-" aus der Discovery-Phase, NICHT den
        # aktuellen Live-Wert. metadata.metadata() entscheidet aber
        # u.a. anhand des Werts, ob der Sensor numerisch ist (siehe
        # has_numeric_value). Deshalb hier den aktuellen Live-Wert aus
        # dem Coordinator einsetzen, bevor die Metadaten berechnet
        # werden - sonst bleiben device_class/unit/precision dauerhaft
        # auf Basis des veralteten Katalog-Platzhalters falsch gesetzt.
        # self.live_entry ist None, solange der Coordinator noch
        # keinen ersten erfolgreichen Refresh hatte - dann wird
        # einfach der statische Katalog-Wert (self.entry.value, meist
        # "-") als live_value verwendet.
        live_value = (
            self.live_entry.value
            if self.live_entry is not None
            else self.entry.value
        )

        return metadata.metadata(
            self.entry,
            self.lookup,
            live_value,
            self.system.enum_texts,
        )

    @property
    def unique_id(self):

        # WICHTIG: Dieses Präfix darf in Zukunft nicht mehr geändert
        # werden, sobald die Integration produktiv läuft! Ändert sich
        # unique_id, legt HA einen komplett NEUEN Registry-Eintrag an
        # (alter Eintrag wird verwaist) - das ist hier bewusst so
        # gewollt, um sicherzustellen, dass suggested_object_id beim
        # allerersten Anlegen ausgewertet wird und nicht ein alter,
        # bereits unter dieser unique_id bestehender Eintrag (mit
        # seiner historisch festgelegten entity_id) wiederverwendet
        # wird.
        return f"windhager_v2_{self.oid}"

    @property
    def device_info(self):

        if self.info is None:
            return None

        module = self.info["module"]

        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"module2_{module.id}",
                )
            },
            manufacturer="Windhager",
            model="InfoWIN",
            name=module.name,
        )

    @property
    def name(self):

        if self.info is None:
            return self.oid

        return naming.build_entity_name(
            self.entry,
            self.lookup,
        )

    @property
    def suggested_object_id(self):
        """Stabilen, lesbaren Object-ID-Vorschlag liefern.

        Wird unabhängig vom (ggf. zusammengesetzten/übersetzten)
        Anzeigenamen aus Modul/Lookup/Entry abgeleitet, damit die
        entity_id auch bei Änderungen an naming.build_entity_name()
        stabil bleibt und keine Kollisionen/Suffixe (_2, _3, ...)
        durch Zufall entstehen.

        module.name wird hier bewusst NICHT mit verarbeitet (siehe
        build_slug in slug.py): Home Assistant stellt bei
        has_entity_name=True automatisch Area- und Geräte-Namen vor
        diesen Object-Id-Teil, sonst entstünde eine Dopplung.
        """

        if self.info is None:
            return None

        module = self.info["module"]

        return build_slug(
            module,
            self.lookup,
            self.entry,
        )

    @property
    def entity_category(self):

        return self.meta.get(
            "entity_category"
        )

    @property
    def entity_registry_enabled_default(self):

        return self.meta.get(
            "enabled_by_default",
            True,
        )

    @property
    def device_class(self):

        # "valid" statt "numeric": Datum/Zeit-Werte sind nicht
        # numerisch (has_numeric_value), aber trotzdem ein gueltiger,
        # typisierter Wert (has_valid_value) - device_class soll fuer
        # beide Faelle gesetzt werden, sofern der Wert kein
        # Platzhalter ("-") ist.
        if not self.meta.get(
            "valid",
            False,
        ):
            return None

        return self.meta.get(
            "device_class"
        )

    @property
    def state_class(self):

        # metadata.state_class() liefert bereits None fuer nicht-
        # numerische Werte und fuer device_classes, bei denen HA
        # keinen state_class erlaubt (DATE, ENUM, ...) - hier nur
        # noch durchreichen.
        return self.meta.get(
            "state_class"
        )

    @property
    def icon(self):

        return self.meta.get(
            "icon"
        )

    @property
    def native_value(self):

        # metadata.parsed_value() wandelt Datum/Zeit-Strings ("20"/
        # "21" Einheit) in echte date/time-Objekte um, wie von HA fuer
        # device_class DATE/TIME gefordert. Fuer alle anderen Faelle
        # liefert es den unveraenderten Rohwert. Faellt auf den
        # statischen Katalog-Wert zurueck, solange noch kein Live-
        # Wert vorliegt (siehe live_entry).
        live_value = (
            self.live_entry.value
            if self.live_entry is not None
            else self.entry.value
        )

        return metadata.parsed_value(
            self.entry,
            live_value,
            self.system.enum_texts,
        )

    @property
    def native_unit_of_measurement(self):

        if not self.meta.get(
            "numeric",
            False,
        ):
            return None

        # Bevorzugt die Einheit aus dem aktuellen Live-Wert (falls
        # vorhanden), da self.entry.unit der statische Katalog-Wert
        # ist. In der Praxis aendert sich die Einheit einer Variable
        # nicht zur Laufzeit, aber so bleibt es konsistent mit der
        # live_value-Logik in self.meta. self.live_entry ist None,
        # solange noch kein erfolgreicher Coordinator-Refresh
        # stattgefunden hat.
        raw_unit = (
            self.live_entry.unit
            if self.live_entry is not None and self.live_entry.unit
            else self.entry.unit
        )

        # Windhager liefert teils eigene/deutsche Einheitenkuerzel
        # (z.B. "Std" statt "h"), die HA fuer die jeweilige
        # device_class nicht akzeptiert - hier auf die von HA
        # erwartete Einheit uebersetzen.
        return metadata.translate_unit(raw_unit)

    @property
    def suggested_display_precision(self):

        # Wie bei native_unit_of_measurement: precision darf nur
        # gesetzt werden, wenn der Wert tatsaechlich numerisch ist.
        # Sonst denkt HA, der Sensor sei numerisch, obwohl er (noch)
        # einen Platzhalterwert wie "-" liefert, und stuerzt beim
        # Schreiben des States ab.
        if not self.meta.get(
            "numeric",
            False,
        ):
            return None

        return self.meta.get(
            "precision"
        )