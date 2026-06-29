# Windhager InfoWIN – Home Assistant Integration

A custom integration for Home Assistant that connects to Windhager
heating systems via the local **InfoWIN** webserver (local network
only, no cloud access needed) and exposes their data as sensors.

> **Note:** This is an independent community project and is not
> affiliated with Windhager Zentralheizung GmbH. "Windhager" is a
> trademark of Windhager Zentralheizung GmbH; it is used here solely
> to identify the supported devices.

## Features

- Automatically discovers all modules, function groups, and
  data points/settings of your installation (no manual entry of
  data points needed)
- Over 350 sensors per installation, including temperatures,
  pressures, pump speeds, status and operating values
- Also exposes around 200 LON network variables (NV's) as additional
  sensors, e.g. operating hours, pellet consumption, number of
  ignition cycles – with readable names for the most common ones
- Sensible Home Assistant metadata (units, device classes, state
  classes for long-term statistics/the Energy dashboard) instead of
  raw values
- Multi-language sensor names (German, English, French, Italian –
  depending on what your Windhager firmware provides), automatically
  matched to your Home Assistant system language
- Separate update interval for regular sensors (default: 5 minutes)
  and NV values (default: 10 minutes), to avoid putting unnecessary
  load on the heating controller
- During setup, you can choose which modules (e.g. individual heating
  circuits) and which sensor groups per module should be created

## Installation

### Via HACS (recommended)

1. Search for "Windhager InfoWIN" in HACS and install it
   *(or add it as a custom repository if it isn't yet listed in the
   default HACS store: HACS → Integrations → three-dot menu → Custom
   repositories → add this repository's URL)*
2. Restart Home Assistant

### Manual

1. Copy the `custom_components/windhager_infowin` folder into the
   `custom_components` directory of your Home Assistant installation
2. Restart Home Assistant

## Setup

1. **Settings → Devices & Services → Add Integration**
2. Search for "Windhager"
3. Enter the following:
   - **Host**: IP address or hostname of the Windhager webserver
     (e.g. `192.168.1.198`)
   - **Username**: Login for the webserver (often `USER` by default
     after a factory reset)
   - **Password**: Password for the webserver (often `123` by
     default after a factory reset)
4. The integration will then read the structure of your system
   (discovery) and let you pick which modules and sensor groups to
   set up – this can take 10–30 seconds depending on the size of
   your installation. The result is cached locally and won't be
   re-fetched on subsequent starts.

### If you don't know the webserver password

If you've used the **Windhager app** (myComfort or similar) to set
up your system, it automatically changes the local webserver's
password when connecting – and never shows it to you in plain text.
In that case, the only way back in is a **factory reset of the
webserver** (reset button on the device, usually held for >10
seconds, see your device's manual), which restores the default
username/password.

**Important:** After a factory reset, the Windhager app generally
won't work with this device anymore, since its setup process would
change the password again – you effectively have to choose between
"app access" and "local API access (e.g. for this integration)",
not both at the same time.

## Compatibility

This integration was developed and tested against a Windhager
installation (BioWIN pellet boiler, built around 2012, multiple
heating circuit modules) with an **InfoWIN Touch** webserver,
hardware model **RC7030**, firmware "S 1.0.2" (2017), **MES
INFINITY** control system.

### Requirements

- A Windhager heating system with **MES INFINITY** control and a
  locally reachable **InfoWIN / InfoWIN Touch / Webserver Touch**
  (hardware model RC7030), reachable via Digest Auth login
- The fuel type (pellets, wood chips, logs, ...) shouldn't matter –
  the data structure (OIDs, LON network variables) is independent of
  the boiler type, as long as the control system is MES INFINITY
  with an RC7030 webserver.

### Probably NOT compatible

- **Newer devices/firmware versions**, where the local web access
  only shows a "comWinStack API" landing page (see e.g.
  [domfie/windhager-rest-api-documentation](https://github.com/domfie/windhager-rest-api-documentation)).
  This API appears to have a different structure than the (older)
  REST API used here – this integration **probably won't work**
  with it without significant changes. If you have such a system and
  want to try it anyway, I'd appreciate a report via Issue (whether
  it works or not).

### Untested / unclear

- The older **MES PLUS** generation (webserver model likely also
  RC7030, but without the "Touch" display) hasn't been tested
  independently, but should work given the shared hardware.

### Known limitations

- Some users report that firmware updates restrict local API access
  afterwards, or that the default login differs after a reset. If
  login doesn't work, a factory reset of the device often helps
  (reset button held for >10 seconds).
- The integration is read-only (sensors only, no write access/control
  of the system).
- The "Modulinfo" sensors (Funktionsbezeichnung, Softwareversion
  Feuerungsautomat, Version HW) show "unknown" on pure heating-circuit
  modules (HK1/HK2/HK3) – this is not a bug in this integration, it
  matches exactly what the official Windhager web interface shows for
  these modules. These fields seem to only be populated on the main
  module with the actual combustion controller (e.g. BioWIN).
- After a power outage (or any abrupt disconnection), the webserver
  has sometimes returned `409 Conflict` errors for a while when polled
  – the webserver itself still answered normally through its own web
  interface during this time, so this appears to be a temporary
  internal state on the device rather than an integration issue. Home
  Assistant's built-in retry mechanism (`ConfigEntryNotReady`) will
  keep retrying automatically (with a backoff capped at 10 minutes,
  but never giving up entirely) until the webserver recovers on its
  own, typically without needing to restart Home Assistant or
  reconfigure the integration.

Feedback on success or problems with other installations/firmware
versions is very welcome via
[GitHub Issues](https://github.com/wiesi12/windhager-tools/issues).


## Contributing

Bug reports, experiences with other installations/firmware versions,
and pull requests are welcome. When reporting an issue, please
include:

- Windhager webserver model and firmware version (see the
  webserver's login page)
- Home Assistant version
- Relevant log output (Settings → System → Logs, filtered by
  "windhager")

## License

See [LICENSE](LICENSE).
