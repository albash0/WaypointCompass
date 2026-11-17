# Preview provenance

`navigation.png`, `gps-search.png`, and `calibration.png` are lossless PNG conversions of the host UI fixtures rendered through Adafruit GFX. They contain synthetic display state and a public city-listed business target. They are not photographs or live GPS/heading measurements.

Generate the source PPM frames from the repository root with:

```sh
sh WaypointCompass/tests/run_tests.sh /tmp/waypointcompass-previews
```

The PNG copies retain pixel data and structural image chunks only.
