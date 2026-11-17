# Waypoint Compass / Bottle Radar

An offline ESP32 GPS compass with a round color display, tilt-compensated heading and saved calibration. Its Bottle Radar mode points toward the nearest city-listed retail liquor store in Boulder, Colorado. Made by [albash0](https://github.com/albash0).

## About the project

The project began as an OLED waypoint compass, then gained a round GC9A01 display, accelerometer-based tilt compensation, custom PCBs and a compact integrated hardware design. Bottle Radar adds automatic target selection, an animated acquisition screen, a mint-and-gold direction arrow, distance and turn cues, GPS diagnostics and a nearby-target celebration.

### Timeline

These dates come from retained sketch/PCB files and dated update records. They are development milestones, not an imported Git commit history.

| Date | Milestone |
| --- | --- |
| 2026-09-29 | Earliest retained OLED waypoint compass sketch: GPS, QMC5883P heading, calibration and a configurable destination. |
| 2026-09-30 | Round TFT bring-up and signal-pin diagnostics. |
| 2026-10-01 | Modular 60 × 40 mm carrier PCB design retained. |
| 2026-10-02 | Compact C1 integrated 54 × 40 mm four-layer PCB design retained, with onboard sensors and battery power circuitry. |
| 2026-10-16 | Bottle Radar update: nearest-of-19 store selection, shared UI/navigation code, GPS reception details, calibration animation and automated navigation/rendering checks. |
| 2026-11-17 | Public source preparation, removal of private waypoint defaults, and self-contained test dependencies. |

## Choose a version

| Version | Sketch | Hardware |
| --- | --- | --- |
| Working module prototype | `WaypointCompass/WaypointCompass.ino` | ESP32-S3 SuperMini, GC9A01 round TFT, GY-271 QMC5883P, GY-521 MPU6050, UART GPS. |
| Compact C1 prototype | `WaypointCompass/CompactPCB/firmware/WaypointCompassCompact/WaypointCompassCompact.ino` | ESP32-S3-MINI-1U-N4R2, LIS2MDL/LIS2DH12 and integrated power circuitry. **Bench-unverified.** |
| Earlier OLED waypoint compass | `WaypointCompassOLED/WaypointCompassOLED.ino` | ESP32-S3 SuperMini, SSD1306 OLED, QMC5883P and UART GPS. Manual destination only. |

[Display behavior, prototype wiring, calibration and serial commands](WaypointCompass/README.md) are documented with the main sketch. KiCad 10 sources, local symbols/footprints, BOMs and unpacked fabrication outputs are under `WaypointCompass/PCB` and `WaypointCompass/CompactPCB`. Supplier module reference solids and prebuilt firmware dumps are omitted; electrical designs remain editable.

## Build

Install Arduino CLI, then from this repository root:

```sh
arduino-cli core update-index --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core install esp32:esp32@3.3.8 --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli lib install TinyGPSPlus "Adafruit GC9A01A" "Adafruit SSD1306"
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc,USBMode=hwcdc,FlashSize=4M --libraries libraries WaypointCompass
```

For C1, enable QSPI PSRAM:

```sh
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc,USBMode=hwcdc,FlashSize=4M,PSRAM=enabled --libraries libraries WaypointCompass/CompactPCB/firmware/WaypointCompassCompact
```

The earlier OLED sketch uses the first profile with `WaypointCompassOLED` as the sketch path. In Arduino IDE, select ESP32S3 Dev Module, 4 MB flash, Hardware CDC/JTAG USB, and USB CDC On Boot. QSPI PSRAM is needed for C1, not for the SuperMini module prototype. Use the matching sketch folder and its accompanying headers.

## Navigation and data

No Wi-Fi, phone, account or API key is needed. Bottle Radar's **19 stores are a 2026-10-16 snapshot** of the [City of Boulder liquor-license map](https://maps.bouldercolorado.gov/liquor-licenses/). Distances are straight-line, not walking directions. Public GIS points are not surveyed entrances; opening hours, business changes and live closures are not checked.

Manual waypoint defaults are unset. Enter `latitude,longitude` in Serial Monitor at 115200 baud to save your own target. `NEAREST` restores automatic mode on the color variants. Saved calibration and destinations stay on the device and are not included in this repository. The older OLED sketch starts without a target until configured; its serial commands differ from Bottle Radar.

Refresh the embedded public dataset with `python3 WaypointCompass/tools/update_store_list.py`, review the new records, then recompile. Both color variants must keep their copied `BoulderStores.h`, `BottleNavigation.h` and `BottleUI.h` files synchronized.

## Compact PCB status

C1 is an unverified hardware prototype. Original records report zero ERC/DRC violations and a successful firmware compile, with configured ignored checks; they do not prove successful hardware operation. Read [the compact board notes](WaypointCompass/CompactPCB/README.md) before fabrication, especially the battery thermistor, polarity and charging requirements. The module carrier's assembly guide is [here](WaypointCompass/PCB/ASSEMBLY.txt).

## Tests

Requires a C++17 compiler with AddressSanitizer and UndefinedBehaviorSanitizer. The vendored Adafruit GFX source is used for real framebuffer rendering.

```sh
sh WaypointCompass/tests/run_tests.sh
```

Tests cover all 19 public store locations, nearest selection, stale/invalid fixes and geographic distance edge cases, and generate eight UI previews. They do not establish sensor calibration accuracy or compact-board hardware operation.

## License

Original project software, documentation and hardware designs: **GPL-2.0-or-later**, except retained third-party notices. See [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md). Public city GIS records retain their source provenance and applicable publisher terms.
