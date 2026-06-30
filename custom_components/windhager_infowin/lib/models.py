from dataclasses import dataclass, field
from typing import Any


@dataclass
class Function:

    id: int
    type: int
    name: str
    locked: bool

    lookups: list["Lookup"] = field(default_factory=list)


@dataclass
class Module:

    id: int
    name: str
    group: str
    subnet: int
    program_id: str
    neuron_id: str

    functions: list[Function] = field(default_factory=list)


@dataclass
class Lookup:

    id: int
    count: int
    name: str = ""

    entries: list = field(default_factory=list)


@dataclass
class Entry:

    oid: str

    value: Any

    unit: str | None

    type_id: int | None

    write_protected: bool

    group: int | None = None
    member: int | None = None

    unit_id: int | None = None
    subtype_id: int | None = None

    min_value: str | None = None
    max_value: str | None = None

    step: str | None = None
    step_id: int | None = None

    timestamp: str | None = None

    # Liste der gueltigen Enum-Werte, falls von der API geliefert
    # (z.B. [0, 1, 2, 3, 4, 5] fuer "Betriebswahl"). Direkter, vom
    # typeId UNABHAENGIGER Marker dafuer, dass dieser Eintrag ein
    # Enum ist - Windhager nutzt mehrere verschiedene typeId-Werte
    # fuer Enums (mindestens 0 und 9 wurden beobachtet), eine
    # vollstaendige typeId-Liste ist mit den verfuegbaren Stichproben
    # nicht zuverlaessig zu pflegen. None bedeutet "kein Enum laut API"
    # (das Feld fehlt schlicht in der Response).
    enum: list[int] | None = None

    name: str = ""

    @property
    def writable(self):

        return not self.write_protected


@dataclass
class NvEntry:

    index: int
    name: str
    snvt_name: str | None
    snvt_index: int | None
    value: object | None
    unit: str | None