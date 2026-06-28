# Windhager InfoWIN – Home Assistant Integration

Eine Custom Integration für Home Assistant, die Windhager-Heizungsanlagen
mit **InfoWIN**-Webserver (lokales Netzwerk, kein Cloud-Zugriff nötig)
als Sensoren einbindet.

> **Hinweis:** Dies ist ein unabhängiges Community-Projekt und steht in
> keiner Verbindung zur Windhager Zentralheizung GmbH. "Windhager" ist
> eine Marke der Windhager Zentralheizung GmbH; die Nennung dient
> ausschließlich der Identifikation der unterstützten Geräte.

## Funktionsumfang

- Automatische Erkennung aller Module, Funktionsgruppen und
  Messwerte/Einstellungen der Anlage (Discovery, kein manuelles
  Eintragen von Datenpunkten nötig)
- Über 350 Sensoren pro Anlage, inklusive Temperaturen, Drücke,
  Drehzahlen, Status- und Betriebswerte
- Zusätzlich rund 200 LON-Netzwerkvariablen (NV's) als eigene Sensoren,
  z. B. Betriebsstunden, Pelletverbrauch, Anzahl Anheizvorgänge – mit
  lesbaren Namen für die wichtigsten Werte
- Sinnvolle Home-Assistant-Metadaten (Einheiten, Device-Klassen,
  State-Klassen für Langzeitstatistiken/Energie-Dashboard) statt
  reiner Rohwerte
- Mehrsprachige Sensor-Namen (Deutsch, Englisch, Französisch,
  Italienisch – je nach Windhager-Firmware verfügbar), automatisch
  passend zur Home-Assistant-Systemsprache
- Getrenntes Update-Intervall für normale Sensoren (Standard: 5 Minuten)
  und für die NV-Werte (Standard: 10 Minuten), um die Heizungssteuerung
  nicht unnötig mit Anfragen zu belasten

## Installation

### Über HACS (empfohlen)

1. In HACS nach "Windhager InfoWIN" suchen und installieren
   *(oder als benutzerdefiniertes Repository hinzufügen, falls noch
   nicht im HACS-Standardverzeichnis gelistet: HACS → Integrationen →
   Drei-Punkte-Menü → Benutzerdefinierte Repositories → diese
   Repository-URL eintragen)*
2. Home Assistant neu starten

### Manuell

1. Den Ordner `custom_components/windhager_infowin` in das
   `custom_components`-Verzeichnis deiner Home-Assistant-Installation
   kopieren
2. Home Assistant neu starten

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen**
2. Nach "Windhager" suchen
3. Folgende Angaben machen:
   - **Host**: IP-Adresse oder Hostname des Windhager-Webservers
     (z. B. `192.168.1.198`)
   - **Benutzername**: Login für den Webserver (Standard nach
     Werksreset häufig `USER`)
   - **Passwort**: Passwort für den Webserver (Standard nach
     Werksreset häufig `123`)
4. Beim ersten Einrichten liest die Integration einmalig die komplette
   Struktur der Anlage aus (Discovery) – das kann je nach Anlagengröße
   10–30 Sekunden dauern. Danach wird das Ergebnis lokal zwischengespeichert
   und beim nächsten Start nicht erneut abgefragt.

## Kompatibilität

Diese Integration wurde entwickelt und getestet mit einer Windhager-Anlage
(BioWIN Pelletkessel, Baujahr ca. 2012, mehrere Heizkreismodule) mit
**InfoWIN Touch** Webserver, Hardware-Modell **RC7030**, Firmware "S 1.0.2"
(2017), Steuerung **MES INFINITY**.

### Voraussetzungen

- Eine Windhager-Heizungsanlage mit **MES INFINITY**-Steuerung und einem
  lokal erreichbaren **InfoWIN / InfoWIN Touch / Webserver Touch**
  (Hardware-Modell RC7030), erreichbar über Digest-Auth-Login
- Der Brennstofftyp (Pellet, Hackschnitzel, Holz, ...) sollte
  keine Rolle spielen – die Datenstruktur (OIDs, LON-Netzwerkvariablen)
  ist unabhängig vom Kesseltyp, solange die Steuerung MES INFINITY mit
  RC7030-Webserver ist.

### Ungetestet / unklar

- Neuere Firmware-Versionen, bei denen der lokale Webzugriff teilweise
  nur noch eine "comWinStack API"-Begrüßungsseite zeigt (siehe z. B.
  [domfie/windhager-rest-api-documentation](https://github.com/domfie/windhager-rest-api-documentation)),
  könnten eine andere/erweiterte API-Schicht verwenden. Diese
  Integration wurde gegen eine ältere Firmware (S 1.0.2, 2017) getestet.
- Die ältere **MES PLUS**-Generation (Webserver-Modell vermutlich ebenfalls
  RC7030, aber ohne "Touch"-Bedienelement) wurde nicht eigenständig
  getestet, dürfte aber aufgrund der baugleichen Hardware ebenfalls
  funktionieren.

### Bekannte Einschränkungen

- Manche Nutzer berichten, dass Firmware-Updates den lokalen API-Zugriff
  nachträglich einschränken oder das Standard-Login nach einem Reset
  abweicht. Falls der Login nicht funktioniert, hilft oft ein Werksreset
  des Geräts (Reset-Taste > 10 Sekunden).
- Die Integration ist read-only (nur Sensoren, kein Schreibzugriff/keine
  Steuerung der Anlage).

Rückmeldungen zu Erfolg oder Problemen auf anderen Anlagen/Firmware-Versionen
sind über [GitHub-Issues](https://github.com/wiesi12/windhager-tools/issues)
herzlich willkommen.

## Mitwirken

Fehlerberichte, Erfahrungen mit anderen Anlagen/Firmware-Versionen und
Pull Requests sind willkommen. Bitte beim Melden eines Problems angeben:

- Windhager-Webserver-Modell und Firmware-Version (siehe Login-Seite
  des Webservers)
- Home-Assistant-Version
- Relevante Logausgabe (Einstellungen → System → Logs, nach
  "windhager" filtern)

## Lizenz

Siehe [LICENSE](LICENSE).