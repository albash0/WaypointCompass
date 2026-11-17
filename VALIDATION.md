# Public source validation — 2026-11-17

Validated against the clean source export using Arduino ESP32 core 3.3.8 and a C++17 host compiler.

- Navigation tests passed under AddressSanitizer/UndefinedBehaviorSanitizer: all 19 public business points, nearest selection, stale/invalid fixes and geographic distance edge cases.
- Eight UI frames rendered through the actual Adafruit GFX renderer.
- SuperMini color, compact C1 color and earlier OLED firmware variants compile. No new physical flash or sensor tests were performed for this publication; C1 remains bench-unverified.
- Private compiled waypoint defaults were removed from all three sketches. Tests use the public city point instead of the former private waypoint fixture. The earlier OLED sketch starts without a configured target.
- The test script creates its preview directory on a fresh checkout.
- Fabrication outputs are byte-identical to the working project's retained outputs. No new ERC/DRC run or hardware fabrication was performed for this export.
- Text and binary-header scans found no known private waypoint, private contact/path, device-MAC or credential patterns in the exported files. Public business coordinates are retained with city-source provenance. Device dumps, logs, local history and firmware binaries were excluded.
- Supplier module models without a local redistribution-license record and derived assembly solids were omitted. The routed electrical design is retained.
- The public repository starts with a fresh history and uses the maintainer's GitHub noreply commit address.

These checks establish software/build consistency, not C1 hardware operation, charging behavior, sensor accuracy or field navigation performance.
