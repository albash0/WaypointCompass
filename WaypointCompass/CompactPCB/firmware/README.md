# Bottle Radar firmware update - 2026-10-16

The compact C1 sketch now defaults to the nearest of 19 City of Boulder retail liquor stores using a fresh GPS fix. It uses the mint/gold Bottle Radar UI, animated acquisition and calibration screens, turn cues and a close-to-target celebration. The earlier build guide's single default destination describes the original firmware; the PCB wiring and assembly instructions still apply.

GPS distances are straight-line. This is an offline snapshot, with no opening-hours or live closure checks. See ../../data/boulder-stores.json for exact records, source query and retrieval date. Store positions are city map points, not surveyed entrances.

Upload WaypointCompassCompact/WaypointCompassCompact.ino with all three .h files in the sketch folder. Board: ESP32S3 Dev Module, 4 MB flash, QSPI PSRAM, Hardware CDC/JTAG, USB CDC On Boot enabled. Existing C1 pin/sensor setup, persistent 10-second calibration and battery ADC are retained. CAL recalibrates; ACTION toggles details.

Serial commands at 115200 with newline: NEAREST, STORES, DETAILS, STATUS, CAL, NMEA, CLEAR or latitude,longitude. Manual coordinates disable nearest mode; NEAREST restores it. The automatic/manual mode persists across resets. Nearest-store updates do not write to flash every second.

Build the matching source sketch; prebuilt firmware images are omitted. C1 hardware remains bench-unverified.
