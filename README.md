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

Rückmeldungen zu Erfolg oder Problemen auf anderen Anlagen/Firmware-Versionen
sind über GitHub-Issues herzlich willkommen.