from config import HOST, USER, PASSWORD

from windhager_tools.client import WindhagerClient
from windhager_tools.system import WindhagerSystem

print("1")

client = WindhagerClient(
    HOST,
    USER,
    PASSWORD,
)

print("2")

system = WindhagerSystem(client)

print("3")

system.initialize()

print("4")

print(len(system.oid_map))

print("5")

print(system.oid_map.get("/1/15/0/0/1/0"))

print("6")