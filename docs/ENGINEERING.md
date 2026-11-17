# Waypoint Compass engineering notes

Waypoint Compass combines GPS position, magnetic heading, accelerometer readings, and a small display. The central challenge is presenting a useful direction while making missing or unreliable input visible.

## Direction needs both position and orientation

A GPS fix supplies position, and the navigation code computes a bearing to a selected target. A magnetometer estimates where the device is facing. The displayed arrow expresses the target bearing relative to that heading.

An accelerometer supplies an estimate of the gravity direction. After calibration and sensor-frame alignment, the firmware projects the magnetic vector and device-forward direction onto the horizontal plane. This reduces the dependence of the heading on how the user tilts the device. It assumes the accelerometer can provide a useful gravity estimate; motion and magnetic interference can still affect the result.

| Input condition | Implemented behavior | Engineering implication |
| --- | --- | --- |
| Fresh GPS fix and valid heading | Show target direction and straight-line distance | Both geographic position and orientation contribute to the arrow. |
| Magnetic heading unavailable | Use GPS course when the speed/validity checks permit; otherwise use a north-up presentation | GPS course describes direction of travel and is not a stationary compass heading. |
| Missing or stale GPS fix | Show acquisition/lost-fix state without a target arrow | Old coordinates should not appear to be a current navigation solution. |
| Calibration requested | Collect samples and store an accepted calibration | Final enclosure placement and nearby conductors/magnets can change calibration conditions. |

The firmware uses a five-second GPS age limit and checks accelerometer recency before tilt compensation. The SuperMini prototype also aligns the magnetometer's frame with the accelerometer frame before projecting the vectors. The compact board uses its own sensor-axis mapping.

Evidence: [SuperMini sensor and navigation firmware](../WaypointCompass/WaypointCompass.ino), [compact-board firmware](../WaypointCompass/CompactPCB/firmware/WaypointCompassCompact/WaypointCompassCompact.ino), [shared display states](../WaypointCompass/BottleUI.h).

## Calibration is not an accuracy specification

The implementation includes magnetic offset/scale calibration, sample validation, a local declination correction, and tilt compensation. These are mechanisms intended to improve heading; they do not establish a measured absolute accuracy.

No heading-error specification is claimed here. A useful next test would compare readings with a reference at several known headings and tilt angles, repeated in the assembled enclosure and with different power conditions. The local declination constant should be updated for use outside the intended region.

## Offline target selection

The Bottle Radar application stores 19 public business locations in flash and selects the nearest one using great-circle distance. A linear scan is appropriate for this small fixed dataset and makes every candidate easy to test. It requires no network connection or external service at runtime.

The distance calculation clamps its intermediate value before square roots to handle floating-point rounding near geographic edge cases. Missing, stale, non-finite, or out-of-range inputs do not produce a selected store.

The tradeoff is data freshness: the embedded city dataset is a dated snapshot, with no opening-hours or live-closure information. The result is straight-line navigation to a map point, not a route to an entrance.

Evidence: [navigation implementation](../WaypointCompass/BottleNavigation.h), [edge-case tests](../WaypointCompass/tests/bottle_navigation_test.cpp), [source dataset and query](../WaypointCompass/data/boulder-stores.json).

## Move from modules toward an integrated PCB

| Design | Purpose | Status |
| --- | --- | --- |
| 60 × 40 mm module carrier | Connect a SuperMini, display, GPS and sensor breakouts with accessible headers | Routed electrical design based on the module prototype. |
| 54 × 40 mm compact C1 | Integrate the MCU, sensors, USB-C and battery power circuitry on a four-layer board | Firmware compiles and historical CAD checks are documented; physical hardware remains unverified. |

Integration reduces dependence on breakout modules but introduces assembly, power, thermal, sensor-placement, and bring-up work. C1 includes battery charging/protection circuitry and requires an external battery thermistor. Its charger and power rails need bench verification before normal battery use.

Evidence: [module assembly guide](../WaypointCompass/PCB/ASSEMBLY.txt), [C1 requirements and status](../WaypointCompass/CompactPCB/README.md).

## What the tests establish

The host suite checks nearest selection at all 19 public points, stale/invalid fixes, and geographic distance edge cases. Eight display states are rendered through the actual Adafruit GFX implementation. Three firmware variants compile.

These checks establish algorithm, renderer and build consistency. They do not measure sensor accuracy, establish C1 charging behavior, or demonstrate field navigation performance. [Public-source validation](../VALIDATION.md).

## Next useful measurements

- Record heading error across orientation and tilt, including repeatability after calibration.
- Compare performance while stationary, walking, and near realistic magnetic interference.
- Measure GPS acquisition time under defined conditions.
- Bring up C1 power rails, thermistor response, charge current, protection and sensors on the bench.
