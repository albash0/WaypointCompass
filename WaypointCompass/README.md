# Waypoint Compass / Bottle Radar

The ESP32 selects the closest of **19 retail liquor stores** from the City of Boulder's public liquor-license map, using the current GPS position. It runs offline: no Wi-Fi, account, phone or API key is needed.

## Screen

- Mint-and-gold arrow, rotating north/cardinal markers and a large distance readout.
- Store name and left/right turn cue; north-up fallback when neither magnetometer heading nor GPS course is available.
- Animated GPS radar while acquiring a fix. No target arrow is shown with a stale or missing fix.
- Animated bottle calibration screen and a "FOUND IT!" celebration within 25 m of the destination's map point.
- Detailed GPS reception page with satellite counts, RX rate, NMEA checksums, SNR and HDOP.

Distances are **straight-line**, not walking routes. The nearest candidate is reevaluated once per second, so the target can change as you move. Store coordinates are city GIS points, not surveyed entrances. The embedded list is a **2026-10-16 snapshot**; opening hours and live closures are not checked. Grocery beer/wine licenses and bars are excluded; the list uses the city's `Retail Liquor Store` class with `STATUS=1`.

## Firmware variants

- `WaypointCompass.ino`: the working SuperMini + QMC5883P GY-271 + MPU6050 GY-521 prototype. The TFT's CS is tied to GND and RST to 3V3, matching its existing running sketch. SCK=10, MOSI=11, DC=13; GPS RX=44/TX=43; I2C SDA=8/SCL=9. GY-271 remains on the GY-521 auxiliary I2C bus with bypass enabled.
- `CompactPCB/firmware/WaypointCompassCompact/WaypointCompassCompact.ino`: the C1 PCB with LIS2MDL/LIS2DH12 and TFT CS=12/RST=6. QSPI PSRAM enabled for its ESP32-S3-MINI-1U-N4R2.

Both variants use the same `BoulderStores.h`, `BottleNavigation.h` and `BottleUI.h`. Their sensor setup, pin configuration, tilt compensation and saved calibration stay specific to their hardware. Keep the copied headers synchronized when editing either firmware.

## Upload and controls

Use ESP32S3 Dev Module, ESP32 Arduino core 3.3.8, 4 MB flash, Hardware CDC/JTAG USB mode and USB CDC On Boot enabled. Install TinyGPSPlus, Adafruit GFX and Adafruit GC9A01A with their dependencies. The prototype does not require PSRAM; C1 uses QSPI PSRAM.

BOOT/CAL starts a 10-second calibration. Roll, pitch and turn the assembled device around all axes; accepted calibration survives resets. The C1 ACTION button toggles detailed diagnostics. Serial Monitor uses 115200 baud with newline endings:

| Command | Action |
| --- | --- |
| `NEAREST` | Enable automatic nearest-store mode; saved across resets. This is the default for the new firmware. |
| `STORES` | Print the embedded store names, addresses and coordinates. |
| `DETAILS` | Toggle the detailed GPS screen. |
| `STATUS` | Report navigation mode, selected store, GPS and sensor status. |
| `CAL` | Start 10-second 3D calibration. |
| `NMEA` | Print five seconds of raw GPS data. |
| `latitude,longitude` | Save a manual waypoint and switch to manual mode. |
| `CLEAR` | Clear the manual target and disable automatic mode. Use NEAREST to resume. |

The old manual waypoint is ignored while automatic mode is active; calibration is retained. Automatic target updates do not write GPS positions to flash.

## Store data and checks

[City liquor-license map](https://maps.bouldercolorado.gov/liquor-licenses/) is linked from the [City licensing page](https://bouldercolorado.gov/services/liquor-licenses). The exact query and records are stored in `data/boulder-stores.json`.

To refresh the list, run `python3 tools/update_store_list.py` with internet access. It queries the city GIS, rejects missing/out-of-area coordinates and regenerates the header in both sketch folders. Recompile and upload afterward. Review business names/status when refreshing.

`tests/run_tests.sh` checks nearest-store selection, missing/stale fixes and geographic distance edge cases under address/undefined-behavior sanitizers. It also renders eight screens with the actual Adafruit GFX implementation for visual inspection. `preview/` contains sample UI images, not live measurements.

Personal waypoints and device backups are excluded from the public source export. Both compiled manual destination defaults are unset (`NAN`). Public city-listed business coordinates remain in the offline dataset.
