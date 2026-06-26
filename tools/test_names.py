from config import HOST, USER, PASSWORD

from windhager_tools.client import WindhagerClient
from windhager_tools.system import WindhagerSystem

client = WindhagerClient(HOST, USER, PASSWORD)
system = WindhagerSystem(client)

system.initialize()

info = system.oid_map["/1/15/0/3/13/0"]

print("MODULE")
print(vars(info["module"]))

print()

print("FUNCTION")
print(vars(info["function"]))

print()

print("LOOKUP")
print(vars(info["lookup"]))

print()

print("ENTRY")
print(vars(info["entry"]))