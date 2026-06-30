from pathlib import Path


DOMAIN = "windhager_infowin"

SCAN_INTERVAL = 30

# Unterordner INNERHALB der Integration selbst (nicht im HA-Config-
# Root) fuer den zwischengespeicherten Discovery-Katalog. Der Vorteil
# gegenueber hass.config.path(): wird der gesamte Integrations-Ordner
# entfernt (z.B. durch HACS-Deinstallation), verschwindet der Katalog
# automatisch mit - es bleiben keine verwaisten Dateien im HA-Config-
# Verzeichnis zurueck. In hacs.json als "persistent_directory"
# deklariert, damit HACS diesen Ordner bei Updates nicht versehentlich
# loescht/ueberschreibt.
#
# Hier in const.py statt nur in __init__.py, damit auch der Options
# Flow (config_flow.py) ohne Duplikation auf denselben Pfad zugreifen
# kann.
DATA_DIR = Path(__file__).parent / "data"