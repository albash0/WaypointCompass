# Waypoint Compass build and installation

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


[Back to project overview](../README.md).
