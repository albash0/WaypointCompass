# Waypoint Compass Compact - C1 prototype

Open `WaypointCompassCompact.kicad_pro` in KiCad 10. The schematic, fully routed PCB and local footprint library are included. This is a new compact design; the working SuperMini/module firmware and original headered carrier remain in their existing folders.

## What is included

- 54 x 40 mm, four-layer, 1.0 mm carrier with the TFT viewing area centered at (27,20) mm.
- Existing inexpensive 7-pin GC9A01 TFT on the front, direct straight male headers and a 2.54 mm board gap.
- Two standard 6 x 6 mm front buttons on the left. Short switches may need case plungers beside the raised display.
- ESP32-S3-MINI-1U-N4R2, LIS2MDL magnetometer and LIS2DH12 accelerometer on the rear. These replace the SuperMini, GY-271 and GY-521 breakout boards. No gyroscope is needed for the current stationary tilt-compensation algorithm.
- USB-C programming and BQ24074 charging with a power path; regulated 3.3 V logic and 5 V TFT/GPS supply; battery protection and a power switch.
- Cable-connected GPS on a JST-SH 4-pin connector. Default 5 V power, selectable 3.3 V; serial signals remain 3.3 V.
- BOM, Gerbers, plated/nonplated drill files, assembly positions, firmware and board documentation.

## Battery and charging

Use a **300-1000 mAh single-cell Li-ion/LiPo intended for 4.2 V charging**. J3 is JST-PH 2-pin: **pin 1 positive, pin 2 cell negative**. Match actual plug polarity; cable colors are not authoritative.

**A separate 10k Semitec 103AT-2 battery thermistor and JST-SH 2-pin cable are required at J5.** Thermally attach the insulated thermistor to the battery. A two-wire battery does not provide this sensor. With J5 empty, charging is inhibited. Charger TS goes to J5 pin 1; J5 pin 2 is system ground. Do not replace the thermistor with a fixed resistor for normal charging.

JP2 open selects about **100 mA**. This is the default for 300-500 mAh cells. Bridge JP2 for about **250 mA** on 500-1000 mAh cells whose manufacturer permits it. For a 1000 mAh cell, use 250 mA mode; at 100 mA it can exceed the charger's timer. Timer is about 9.53 hours nominal, with IC tolerance approximately 7.15-11.92 hours. USB input mode is fixed at 500 mA; the power path reduces charge current when the running load needs the available input current. Switching the device off disables the two regulators while USB charging remains available.

Cell-negative and system GND are separate nets joined by the protection MOSFETs. **Do not wire J3 pin 2 to a system-GND test pad**, because that bypasses protection.

## Build and prototype verification

C1 is a **bench-unverified prototype**. KiCad ERC: 0 violations. PCB DRC: 0 violations, 0 unconnected items and 0 schematic parity issues with the supplied rules; the reports list configured ignored checks. Firmware compiles with ESP32 Arduino core 3.3.8. These checks establish file consistency, not successful hardware operation or charging certification.

Use SMT assembly/reflow for the LGA, QFN, SON and WSON packages. Most passives are 0603; R19/R20 are 0402. Hand solder the front buttons, TFT header and rear JST-PH battery connector. Supply the assembler with BOM, position CSV, native project and component orientation information. Confirm actual MPN availability and permitted substitutions at ordering.

Before using the battery charger, verify power rails, charge current, NTC response, protection behavior, temperature and sensors on the bench. Keep the battery and its cable away from the magnetometer; recalibrate in the final assembled enclosure and check heading while charging.

## Firmware

**2026-10-16 update:** Bottle Radar now selects the nearest of 19 city-listed Boulder retail liquor stores. See `firmware/README.md` for current UI and commands; the build guide describes the original firmware.

Sketch: `firmware/WaypointCompassCompact/WaypointCompassCompact.ino`.

Arduino IDE board: ESP32S3 Dev Module; 4 MB flash; QSPI PSRAM; Hardware CDC/JTAG USB; USB CDC On Boot enabled. Install TinyGPSPlus, Adafruit GFX, Adafruit GC9A01A and their Library Manager dependencies.

- Default mode: nearest city-listed Boulder liquor store. Manual coordinates remain available over USB.
- First startup runs 10-second 3D calibration; rotate the complete device around all axes. Valid calibration is saved across resets.
- CAL button repeats calibration. Holding CAL while resetting enters the USB ROM bootloader; release CAL after entering the bootloader.
- ACTION toggles GPS diagnostics. Serial commands at 115200: `NEAREST`, `STORES`, `DETAILS`, `STATUS`, `NMEA`, `CAL`, `CLEAR`, or `latitude,longitude`.
- GPS defaults to 9600 baud. GPIO44 receives GPS TX; GPIO43 transmits to GPS RX.
- Compact sensor mapping matches rear-mounted C1 footprints. Verify +Z gravity is approximately +1 g with the screen face up, and check compass direction/tilt on the first board.
- Battery voltage in Serial STATUS is an ADC estimate, not a percentage gauge.

Compile command (with arduino-cli installed):

```sh
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc,USBMode=hwcdc,FlashSize=4M,PSRAM=enabled firmware/WaypointCompassCompact
```

## Public source files

Native KiCad schematic, routed PCB, local symbols/footprints, BOM and unpacked fabrication outputs are included. Supplier 3D references, derived assembly solids, historical ZIPs, prebuilt firmware and local CAD history are omitted. Model paths may refer to omitted visualization assets; they do not affect copper or fabrication. Use the schematic and BOM to review the design.

The native files are the design authority. Development scripts are retained as references; running `build_compact.py --board` regenerates an unrouted board and overwrites the routed layout. Work in a separate copy before regenerating.
