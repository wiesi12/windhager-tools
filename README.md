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
- **Write support** *(experimental – use at your own risk)*:
  writable values appear as interactive entities –
  temperature setpoints (e.g. room temperature setpoint, setback
  temperature) as number inputs with the correct bounds and step size
  directly from the device, operating modes (e.g. Betriebswahl:
  Standby / Heizprogramm 1 / ...) as dropdowns with human-readable
  labels. Changes are confirmed immediately in the UI without waiting
  for the next polling cycle.

  > ⚠️ Write support has only been tested on a single installation
  > (BioWIN pellet boiler, firmware S 1.0.2). It uses the same local
  > API endpoint as the official Windhager web interface, with the
  > same ENDUSER credentials – but incorrect values sent to a heating
  > system can cause real problems. Double-check any value you set,
  > and verify the result in the Windhager web interface. **Use at
  > your own risk.** Feedback on what works (or doesn't) with other
  > installations is very welcome via GitHub Issues.
- **Time programs** *(experimental – use at your own risk)*: heating
  circuit and domestic hot water time programs ("Zeitprogramm 1/2/3",
  "Warmwasser Zeitprogramm", etc.) are exposed as sensors showing
  their switch points/weekdays as attributes, and can be changed via
  the `windhager_infowin.set_schedule` service (see `services.yaml`
  for the exact fields, including support for multiple switch-point
  groups per program, e.g. different values for weekdays vs. Sunday).
  Detection is fully generic: it reads the device's own
  `res/xml/StaticNav.xml` resource for the list of available time
  program positions and their real (translated) names, instead of a
  hardcoded list – so it should work on any installation, not just
  this developer's. Only verified on a single installation so far. If
  it doesn't find any schedules on your installation, please report
  it via GitHub Issues.
- **Time program card** *(experimental)*: an optional Lovelace card
  for comfortably viewing/editing a time program instead of raw
  sensor attributes/Developer Tools YAML - lives in its own repository
  for separate HACS (Dashboard/plugin) distribution:
  [windhager-schedule-card](https://github.com/wiesi12/windhager-schedule-card).
- **PMX combustion state sensor** *(BioWIN / PMX controller only)*:
  the internal PMX controller state (NV index 27) is translated into
  readable German labels (Standby, Zündvorbereitung, Zündung,
  Hochbrennen, Volllast, Modulation, Bereitschaft) instead of raw
  hex values. Unknown states from other firmware versions fall back
  to the raw hex value so data collection is never interrupted.
- **"Jetzt aktualisieren" button**: trigger an immediate poll of all
  sensors or NV values without reloading the integration – useful
  after changing a setpoint or operating mode.
- **NV sensor groups**: NV sensors (LON network variables) can be
  filtered by group based on their standardized LON data type
  (`snvt_name`) — Temperatures, Power & RPM, Counters & Runtimes,
  Operation & Status, Other. Works across all installations regardless
  of NV names. Configurable via the Options Flow after first setup.
- **Pellet consumption sensor** *(BioWIN only)*: dedicated sensor for
  pellet consumption total (NV index 19) with a configurable unit
  factor. On a BioWIN 2 Touch, 1 raw unit = 10 kg — set the factor
  to 10 in the Options Flow to get the result in tonnes.
- **Last known state on startup**: all sensors show their last known
  value immediately after a restart instead of "Unknown" while waiting
  for the first coordinator refresh (~18s sensors, ~25s NV values).
- Sensible Home Assistant metadata (units, device classes, state
  classes for long-term statistics/the Energy dashboard) instead of
  raw values
- Multi-language sensor names (German, English, French, Italian –
  depending on what your Windhager firmware provides), automatically
  matched to your Home Assistant system language
- **Configurable poll intervals**: choose how often the integration
  polls your heating system (default: 1 minute for sensors, 5 minutes
  for NV values) via the Options Flow
- During setup, you can choose which modules (e.g. individual heating
  circuits) and which sensor groups per module should be created –
  this selection can be changed at any time afterwards via
  **Settings → Devices & Services → Windhager InfoWIN → Configure**

## First-time setup notes

A few things are only configurable **after** the initial setup
completes, via **Settings → Devices & Services → Windhager InfoWIN →
Configure**:

- **NV sensor groups**: on initial installation, all NV groups are
  included by default. To exclude groups you don't need (e.g. system
  internals under "Betrieb & Status"), open Configure and deselect
  them in the "NV sensor groups" step.

- **Pellet consumption factor**: if your installation is a BioWIN
  pellet boiler, set the factor to **10** (1 raw unit = 10 kg, result
  shown in tonnes). The default is 1.0 (raw value, no conversion).
  You'll find this in the "Sensor calibration" step.

- **The integration catalog** (the discovered structure of your
  heating system) is stored in the integration's data directory and
  intentionally **not deleted** when you remove the integration — this
  means a reinstall skips the ~30s discovery crawl and starts up
  immediately. If you want a fresh discovery (e.g. after a firmware
  update), delete the `catalog_*.json` file from
  `custom_components/windhager_infowin/data/` before reinstalling.

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

If you've previously set up the **Windhager app** (myComfort/Windhager
Connect) with your system, it may have changed the local webserver's
password during that initial pairing process, without ever showing
it to you in plain text. In that case, two options to get back in:

- If you have access to the [Windhager Connect](https://connect.windhager.com)
  web portal (same login as the app), there may be a "Change webserver
  password" option under your system's settings that lets you reset
  it to the default (`123`) directly – this didn't appear to be
  available on every account/system in informal testing, so YMMV.
- Otherwise, a **factory reset of the webserver** (reset button on
  the device, usually held for >10 seconds, see your device's manual)
  restores the default username/password.

Note that the app reconnecting to your system afterwards does **not**
necessarily mean it changed the password again – in practice, the
password only seems to get changed during the *initial* pairing, not
on every reconnect. So app and local API access aren't necessarily
mutually exclusive in the long run, though this hasn't been tested
thoroughly across different firmware versions.

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
- A single poll takes approximately 17–20 seconds, so poll intervals
  below 30 seconds are not useful in practice. The NV poll takes
  approximately 25–30 seconds.

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
