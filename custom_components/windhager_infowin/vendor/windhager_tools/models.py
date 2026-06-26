from dataclasses import dataclass, field


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
    value: str
    unit: str
    type_id: int
    write_protected: bool

    group: int | None = None
    member: int | None = None

    name: str = ""


@dataclass
class NvEntry:

    index: int
    name: str
    snvt_name: str | None
    snvt_index: int | None
    value: object | None
    unit: str | None