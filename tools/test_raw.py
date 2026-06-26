from pprint import pprint

from config import HOST, USER, PASSWORD

from windhager_tools.client import WindhagerClient


client = WindhagerClient(
    HOST,
    USER,
    PASSWORD,
)

data = client.lookup(
    "1/15/0/113"
)

print(type(data))
print()

pprint(data)