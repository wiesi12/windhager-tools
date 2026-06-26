from config import HOST, USER, PASSWORD

from windhager_tools.client import WindhagerClient
from windhager_tools.resources import (
    ResourceDatabase,
)


client = WindhagerClient(
    HOST,
    USER,
    PASSWORD,
)

resources = ResourceDatabase()

resources.load(client)

print()

print(
    resources.level_name(
        14,
        113,
    )
)

print(
    resources.level_name(
        14,
        117,
    )
)

print(
    resources.level_name(
        15,
        100,
    )
)

print()

print(
    resources.variable_name(
        0,
        1,
    )
)

print(
    resources.variable_name(
        1,
        1,
    )
)

print(
    resources.variable_name(
        2,
        9,
    )
)