from xml.etree import ElementTree

from config import HOST, USER, PASSWORD

from windhager_tools.client import WindhagerClient


client = WindhagerClient(
    HOST,
    USER,
    PASSWORD,
)

xml = client.resource(
    "xml/VarIdentTexte_de.xml"
)

root = ElementTree.fromstring(xml)

print(root.tag)

for child in root[:3]:
    print()
    print(child.tag, child.attrib)

    for sub in child[:5]:
        print("   ", sub.tag, sub.attrib, sub.text)