#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <Preferences.h>
#include <TinyGPS++.h>
#include <Adafruit_GFX.h>
#include <Adafruit_GC9A01A.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include "BottleUI.h"

// ESP32-S3 SuperMini pins. Change these if your particular board labels differ.
constexpr int GPS_RX = 44;  // ESP32 RX pad <- GPS TX
constexpr int GPS_TX = 43;  // ESP32 TX pad -> GPS RX (optional)
constexpr int TFT_SCK = 10; // Display SCL/CLK; this is SPI, not I2C
constexpr int TFT_MOSI = 11;// Display SDA/DIN; this is SPI, not I2C
constexpr int TFT_CS = -1; // TFT CS tied to GND; GPIO12 is not used.
constexpr int TFT_DC = 13;
constexpr int TFT_RST = -1; // TFT RST/RES tied to 3V3.
constexpr int MAG_SDA = 8;
constexpr int MAG_SCL = 9;
constexpr uint8_t MAG_ADDRESS = 0x2C; // Verified QMC5883P GY-271
// GY-521/MPU-6050 sits on GPIO8/9. Its XDA/XCL pins carry the GY-271
// after I2C bypass is enabled. These signs assume matching X/Y board axes.
constexpr float IMU_X_SIGN = 1.0f;
constexpr float IMU_Y_SIGN = 1.0f;
constexpr float IMU_Z_SIGN = 1.0f;

constexpr uint32_t GPS_BAUD = 9600;
constexpr uint32_t FIX_MAX_AGE_MS = 5000;
constexpr float MIN_COURSE_SPEED_MPS = 1.2f;
constexpr uint32_t DRAW_PERIOD_MS = 150;
constexpr uint32_t CAL_DURATION_MS = 10000;
constexpr int CAL_BUTTON_PIN = 0; // ESP32-S3 SuperMini BOOT button, pressed after boot.
constexpr size_t CAL_MAX_SAMPLES = 200;
constexpr float DECLINATION_DEG = 7.7f; // Approximate near Boulder, CO in 2026
constexpr float MOUNT_OFFSET_DEG = 0.0f; // Quarter-turn frame alignment is applied to the magnetic vector.

// Optional destination compiled into the sketch. Set both to real coordinates
// for a first-use default, or leave as NAN and enter them over USB Serial.
constexpr double DEFAULT_LAT = NAN;
constexpr double DEFAULT_LON = NAN;

constexpr uint16_t BLACK = 0x0000;
constexpr uint16_t WHITE = 0xFFFF;
constexpr uint16_t GRAY = 0x7BEF;
constexpr uint16_t GREEN = 0x07E0;
constexpr uint16_t AMBER = 0xFD20;
constexpr uint16_t RED = 0xF800;
constexpr uint16_t CYAN = 0x07FF;

HardwareSerial gpsSerial(1); // Keep USB Serial separate from the GPS UART.
TinyGPSPlus gps;
TinyGPSCustom gpsFixQuality(gps, "GPGGA", 6);
TinyGPSCustom gpsSatellitesInView(gps, "GPGSV", 3);
TinyGPSCustom gsvTotalMessages(gps, "GPGSV", 1);
TinyGPSCustom gsvMessageNumber(gps, "GPGSV", 2);
TinyGPSCustom gsvSnr1(gps, "GPGSV", 7);
TinyGPSCustom gsvSnr2(gps, "GPGSV", 11);
TinyGPSCustom gsvSnr3(gps, "GPGSV", 15);
TinyGPSCustom gsvSnr4(gps, "GPGSV", 19);
Adafruit_GC9A01A tft(&SPI, TFT_DC, TFT_CS, TFT_RST);
GFXcanvas16 frame(240, 240); // Compose offscreen so updates do not flash black.
Adafruit_GFX &gfx = frame.getBuffer() ? static_cast<Adafruit_GFX &>(frame)
                                      : static_cast<Adafruit_GFX &>(tft);
Preferences prefs;

double destinationLat = NAN;
double destinationLon = NAN;
bool destinationSet = false;
bool automaticStoreMode = true;
int selectedStore = -1;
uint32_t lastNearestUpdateMs = 0;
float displayHeading = NAN;
bool forceGpsDiagnostics = false;

char commandLine[72];
size_t commandLength = 0;
bool commandOverflow = false;
uint32_t lastDrawMs = 0;
bool redrawRequested = true;
uint32_t lastGpsStatsMs = 0;
uint32_t lastGpsChars = 0;
uint32_t lastGpsPassed = 0;
uint32_t lastGpsFailed = 0;
uint32_t gpsCharsPerSecond = 0;
uint32_t gpsValidPerSecond = 0;
uint32_t gpsBadPerSecond = 0;
uint32_t rawNmeaUntilMs = 0;
int gpsTrackedSignals = -1;
int gpsMaxSnr = -1;
int gsvCycleTracked = 0;
int gsvCycleMaxSnr = 0;
uint32_t lastGsvCycleMs = 0;
bool magOk = false;
bool magFresh = false;
bool imuOk = false;
bool accelFresh = false;
bool tiltHeadingUsed = false;
uint8_t imuAddress = 0;
bool calibrated = false;
bool calibrating = false;
bool calibrationFailed = false;
bool calButtonWasDown = false;
uint32_t lastMagReadMs = 0;
uint32_t lastMagSuccessMs = 0;
uint32_t lastAccelReadMs = 0;
uint32_t lastAccelSuccessMs = 0;
uint32_t calStartMs = 0;
uint32_t lastReportMs = 0;
uint32_t lastFrameDurationUs = 0;
uint32_t lastCalButtonMs = 0;
uint32_t rejectedMagSamples = 0;
int16_t magX = 0, magY = 0, magZ = 0;
struct MagSample { int16_t x, y, z; };
MagSample calSamples[CAL_MAX_SAMPLES];
size_t calSampleCount = 0;
float calMinAccelX = 1, calMinAccelY = 1, calMinAccelZ = 1;
float calMaxAccelX = -1, calMaxAccelY = -1, calMaxAccelZ = -1;
float magOffsetX = 0, magOffsetY = 0, magOffsetZ = 0;
float magScaleX = 1, magScaleY = 1, magScaleZ = 1;
float magFieldRadius = 0;
float trueHeading = NAN;
float accelX = 0, accelY = 0, accelZ = 0;
float accelMagnitudeG = NAN;
float pitchDeg = NAN, rollDeg = NAN;

float normalizedDegrees(float degreesValue);

bool writeMag(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MAG_ADDRESS);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readMag(uint8_t reg, uint8_t *out, uint8_t count) {
  Wire.beginTransmission(MAG_ADDRESS);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(MAG_ADDRESS, count) != count) return false;
  for (uint8_t i = 0; i < count; ++i) out[i] = Wire.read();
  return true;
}

bool writeImu(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(imuAddress);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readImu(uint8_t address, uint8_t reg, uint8_t *out, uint8_t count) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(address, count) != count) return false;
  for (uint8_t i = 0; i < count; ++i) out[i] = Wire.read();
  return true;
}

bool startImu() {
  uint8_t who = 0;
  for (uint8_t address : {0x68, 0x69}) {
    if (readImu(address, 0x75, &who, 1) && who == 0x68) {
      imuAddress = address;
      break;
    }
  }
  if (!imuAddress) {
    Serial.println("GY-521: MPU-6050 not found at 0x68/0x69");
    return false;
  }
  // Wake MPU-6050, leave its own I2C master off, then bridge SDA/SCL to XDA/XCL.
  const bool ok = writeImu(0x6B, 0x01) &&
                  writeImu(0x1A, 0x03) &&
                  writeImu(0x1C, 0x00) &&
                  writeImu(0x6A, 0x00) &&
                  writeImu(0x37, 0x02);
  delay(50);
  Serial.printf("GY-521 MPU-6050 at 0x%02X: %s; XDA/XCL bypass %s\n",
                imuAddress, ok ? "ready" : "init failed", ok ? "on" : "failed");
  return ok;
}

void updateImu(uint32_t now) {
  if (!imuOk || now - lastAccelReadMs < 50) return;
  lastAccelReadMs = now;
  uint8_t data[6];
  if (!readImu(imuAddress, 0x3B, data, 6)) return;
  const int16_t rawX = (int16_t)((data[0] << 8) | data[1]);
  const int16_t rawY = (int16_t)((data[2] << 8) | data[3]);
  const int16_t rawZ = (int16_t)((data[4] << 8) | data[5]);
  const float x = IMU_X_SIGN * rawX / 16384.0f;
  const float y = IMU_Y_SIGN * rawY / 16384.0f;
  const float z = IMU_Z_SIGN * rawZ / 16384.0f;
  const float magnitude = sqrtf(x * x + y * y + z * z);
  accelMagnitudeG = magnitude;
  if (magnitude < 0.75f || magnitude > 1.25f) return;
  if (calibrating) {
    calMinAccelX = fminf(calMinAccelX, x);
    calMinAccelY = fminf(calMinAccelY, y);
    calMinAccelZ = fminf(calMinAccelZ, z);
    calMaxAccelX = fmaxf(calMaxAccelX, x);
    calMaxAccelY = fmaxf(calMaxAccelY, y);
    calMaxAccelZ = fmaxf(calMaxAccelZ, z);
  }
  if (!accelFresh) {
    accelX = x;
    accelY = y;
    accelZ = z;
  } else {
    accelX = 0.8f * accelX + 0.2f * x;
    accelY = 0.8f * accelY + 0.2f * y;
    accelZ = 0.8f * accelZ + 0.2f * z;
  }
  lastAccelSuccessMs = now;
  accelFresh = true;
  pitchDeg = atan2f(-accelX, sqrtf(accelY * accelY + accelZ * accelZ)) * 180.0f / PI;
  rollDeg = atan2f(accelY, accelZ) * 180.0f / PI;
}

bool startMagnetometer() {
  uint8_t id = 0;
  if (!readMag(0x00, &id, 1) || id != 0x80) {
    Serial.printf("GY-271: expected QMC5883P ID 0x80; got 0x%02X\n", id);
    return false;
  }
  const bool ok = writeMag(0x29, 0x06) &&
                  writeMag(0x0B, 0x08) &&
                  writeMag(0x0A, 0xC5);
  Serial.printf("GY-271 QMC5883P: %s\n", ok ? "ready" : "init failed");
  return ok;
}

int compareInt16(const void *left, const void *right) {
  return (int)*(const int16_t *)left - (int)*(const int16_t *)right;
}

void finishCalibration() {
  calibrating = false;
  const bool coveredGravity = calMinAccelX < -0.35f && calMaxAccelX > 0.35f &&
                              calMinAccelY < -0.35f && calMaxAccelY > 0.35f &&
                              calMinAccelZ < -0.35f && calMaxAccelZ > 0.35f;
  if (calSampleCount < 50 || !coveredGravity) {
    calibrationFailed = true;
    Serial.printf("CAL incomplete: %u mag samples; gravity X %.2f..%.2f Y %.2f..%.2f Z %.2f..%.2f g. Rotate around all axes.\n",
                  (unsigned)calSampleCount, calMinAccelX, calMaxAccelX,
                  calMinAccelY, calMaxAccelY, calMinAccelZ, calMaxAccelZ);
    redrawRequested = true;
    return;
  }
  // Ignore the outer 5% so one magnetic glitch cannot set the offsets.
  int16_t sortedX[CAL_MAX_SAMPLES], sortedY[CAL_MAX_SAMPLES], sortedZ[CAL_MAX_SAMPLES];
  for (size_t i = 0; i < calSampleCount; ++i) {
    sortedX[i] = calSamples[i].x;
    sortedY[i] = calSamples[i].y;
    sortedZ[i] = calSamples[i].z;
  }
  qsort(sortedX, calSampleCount, sizeof(int16_t), compareInt16);
  qsort(sortedY, calSampleCount, sizeof(int16_t), compareInt16);
  qsort(sortedZ, calSampleCount, sizeof(int16_t), compareInt16);
  const size_t low = calSampleCount / 20;
  const size_t high = calSampleCount - 1 - low;
  const int32_t rangeX = (int32_t)sortedX[high] - sortedX[low];
  const int32_t rangeY = (int32_t)sortedY[high] - sortedY[low];
  const int32_t rangeZ = (int32_t)sortedZ[high] - sortedZ[low];
  const int32_t smallestRange = min(rangeX, min(rangeY, rangeZ));
  const int32_t largestRange = max(rangeX, max(rangeY, rangeZ));
  if (smallestRange < 400 || smallestRange < largestRange * 0.4f) {
    calibrationFailed = true;
    Serial.printf("CAL incomplete: magnetic ranges X=%ld Y=%ld Z=%ld; rotate more fully.\n",
                  (long)rangeX, (long)rangeY, (long)rangeZ);
    redrawRequested = true;
    return;
  }
  magOffsetX = ((float)sortedX[high] + sortedX[low]) * 0.5f;
  magOffsetY = ((float)sortedY[high] + sortedY[low]) * 0.5f;
  magOffsetZ = ((float)sortedZ[high] + sortedZ[low]) * 0.5f;
  const float averageRange = ((float)rangeX + rangeY + rangeZ) / 3.0f;
  magScaleX = averageRange / rangeX;
  magScaleY = averageRange / rangeY;
  magScaleZ = averageRange / rangeZ;
  magFieldRadius = averageRange * 0.5f;
  calibrated = true;
  calibrationFailed = false;
  prefs.putFloat("magOffX", magOffsetX);
  prefs.putFloat("magOffY", magOffsetY);
  prefs.putFloat("magOffZ", magOffsetZ);
  prefs.putFloat("magScX", magScaleX);
  prefs.putFloat("magScY", magScaleY);
  prefs.putFloat("magScZ", magScaleZ);
  prefs.putFloat("magRadius", magFieldRadius);
  prefs.putUInt("calVersion", 2);
  Serial.printf("3D CAL saved: X %.1f/%.3f, Y %.1f/%.3f, Z %.1f/%.3f, radius %.1f\n",
                magOffsetX, magScaleX, magOffsetY, magScaleY,
                magOffsetZ, magScaleZ, magFieldRadius);
  redrawRequested = true;
}

void startCalibration() {
  calSampleCount = 0;
  calMinAccelX = calMinAccelY = calMinAccelZ = 1.0f;
  calMaxAccelX = calMaxAccelY = calMaxAccelZ = -1.0f;
  calStartMs = millis();
  calibrating = true;
  calibrationFailed = false;
  redrawRequested = true;
  Serial.println("3D CAL started: roll, pitch, and turn the device through all orientations for 10 seconds.");
}

void updateMagnetometer(uint32_t now) {
  if (!magOk || now - lastMagReadMs < 50) return;
  lastMagReadMs = now;
  uint8_t status = 0;
  if (!readMag(0x09, &status, 1) || !(status & 1) || (status & 2)) return;
  uint8_t data[6];
  if (!readMag(0x01, data, 6)) return;
  magX = (int16_t)((data[1] << 8) | data[0]);
  magY = (int16_t)((data[3] << 8) | data[2]);
  magZ = (int16_t)((data[5] << 8) | data[4]);
  if (calibrating && calSampleCount < CAL_MAX_SAMPLES) {
    calSamples[calSampleCount++] = {magX, magY, magZ};
  }
  const float correctedX = (magX - magOffsetX) * magScaleX;
  const float correctedY = (magY - magOffsetY) * magScaleY;
  const float z = (magZ - magOffsetZ) * magScaleZ;
  // The measured compass frame is a quarter-turn from the +X-forward IMU
  // frame. Rotate the vector before tilt compensation, not the final heading.
  const float x = correctedY;
  const float y = -correctedX;
  const float fieldStrength = sqrtf(x * x + y * y + z * z);
  if (calibrated && !calibrating && magFieldRadius > 1.0f &&
      (fieldStrength < 0.45f * magFieldRadius ||
       fieldStrength > 2.2f * magFieldRadius)) {
    ++rejectedMagSamples;
    return;
  }
  lastMagSuccessMs = now;
  magFresh = true;
  float northX = x;
  float northY = y;
  tiltHeadingUsed = false;
  if (calibrated && accelFresh && now - lastAccelSuccessMs <= 500) {
    const float length = sqrtf(accelX * accelX + accelY * accelY + accelZ * accelZ);
    if (length > 0.5f) {
      // Project magnetic north and the device's +X/front axis onto the
      // horizontal plane. Flat orientation reduces exactly to atan2(Y, X).
      float ax = accelX / length;
      float ay = accelY / length;
      float az = accelZ / length;
      const float verticalField = ax * x + ay * y + az * z;
      const float projectedX = x - ax * verticalField;
      const float projectedY = az * y - ay * z;
      if (1.0f - ax * ax > 0.06f && hypotf(projectedX, projectedY) > 1.0f) {
        northX = projectedX;
        northY = projectedY;
        tiltHeadingUsed = true;
      }
    }
  }
  trueHeading = normalizedDegrees(atan2f(northY, northX) * 180.0f / PI +
                                  DECLINATION_DEG + MOUNT_OFFSET_DEG);
}

void recordGsvSignal(TinyGPSCustom &field) {
  if (!field.isUpdated()) return;
  const int snr = atoi(field.value());
  if (snr > 0) {
    ++gsvCycleTracked;
    if (snr > gsvCycleMaxSnr) gsvCycleMaxSnr = snr;
  }
}

void updateGsvCycle() {
  if (!gsvMessageNumber.isUpdated()) return;
  const int message = atoi(gsvMessageNumber.value());
  const int total = atoi(gsvTotalMessages.value());
  if (message == 1) {
    gsvCycleTracked = 0;
    gsvCycleMaxSnr = 0;
  }
  recordGsvSignal(gsvSnr1);
  recordGsvSignal(gsvSnr2);
  recordGsvSignal(gsvSnr3);
  recordGsvSignal(gsvSnr4);
  if (total > 0 && message == total) {
    gpsTrackedSignals = gsvCycleTracked;
    gpsMaxSnr = gsvCycleMaxSnr;
    lastGsvCycleMs = millis();
  }
}

int recentTrackedSignals() {
  return lastGsvCycleMs != 0 && millis() - lastGsvCycleMs < FIX_MAX_AGE_MS
             ? gpsTrackedSignals : -1;
}

int recentMaxSnr() {
  return lastGsvCycleMs != 0 && millis() - lastGsvCycleMs < FIX_MAX_AGE_MS
             ? gpsMaxSnr : -1;
}

void updateGpsStats(uint32_t now) {
  const uint32_t elapsed = now - lastGpsStatsMs;
  if (elapsed < 1000) return;
  gpsCharsPerSecond = (gps.charsProcessed() - lastGpsChars) * 1000UL / elapsed;
  gpsValidPerSecond = (gps.passedChecksum() - lastGpsPassed) * 1000UL / elapsed;
  gpsBadPerSecond = (gps.failedChecksum() - lastGpsFailed) * 1000UL / elapsed;
  lastGpsChars = gps.charsProcessed();
  lastGpsPassed = gps.passedChecksum();
  lastGpsFailed = gps.failedChecksum();
  lastGpsStatsMs = now;
}

int gpsViewCount() {
  return gpsSatellitesInView.isValid() && gpsSatellitesInView.age() < FIX_MAX_AGE_MS
             ? atoi(gpsSatellitesInView.value()) : -1;
}

int gpsQuality() {
  return gpsFixQuality.isValid() && gpsFixQuality.age() < FIX_MAX_AGE_MS
             ? atoi(gpsFixQuality.value()) : -1;
}

void saveDestination(double lat, double lon) {
  automaticStoreMode = false;
  selectedStore = -1;
  prefs.putBool("autoStore", false);
  destinationLat = lat;
  destinationLon = lon;
  destinationSet = true;
  prefs.putDouble("lat", lat);
  prefs.putDouble("lon", lon);
  prefs.putBool("set", true);
  redrawRequested = true;
  Serial.printf("Destination saved: %.7f, %.7f\n", lat, lon);
}

void printStatus() {
  Serial.printf("Bottle Radar / %s / %u city-listed stores / map 2026-10-16\n",
                automaticStoreMode ? "NEAREST" : "MANUAL", (unsigned)bottle::STORE_COUNT);
  if (selectedStore >= 0) Serial.printf("Store: %s / %s\n", bottle::STORES[selectedStore].name, bottle::STORES[selectedStore].address);
  if (destinationSet) Serial.printf("Destination: %.7f, %.7f\n", destinationLat, destinationLon);
  else if (automaticStoreMode) Serial.println("Nearest store: waiting for a fresh GPS fix.");
  else Serial.println("No manual waypoint. Send NEAREST or latitude,longitude.");
  if (gps.location.isValid()) {
    Serial.printf("GPS: %.6f, %.6f; age %lu ms; satellites %lu\n",
                  gps.location.lat(), gps.location.lng(), gps.location.age(),
                  gps.satellites.isValid() ? gps.satellites.value() : 0UL);
  } else {
    Serial.println("No current GPS fix.");
  }
  Serial.printf("GPS UART: %lu chars total, %lu chars/s; NMEA: %lu valid, %lu bad checksum\n",
                gps.charsProcessed(), gpsCharsPerSecond,
                gps.passedChecksum(), gps.failedChecksum());
  Serial.printf("GGA fix quality: %d; satellites used: %ld; satellites in view: %d; HDOP: ",
                gpsQuality(),
                gps.satellites.isValid() && gps.satellites.age() < FIX_MAX_AGE_MS
                    ? (long)gps.satellites.value() : -1L,
                gpsViewCount());
  if (gps.hdop.isValid() && gps.hdop.age() < FIX_MAX_AGE_MS)
    Serial.println(gps.hdop.hdop(), 1);
  else
    Serial.println("unknown");
  Serial.printf("GSV signals with SNR: %d; strongest SNR: %d dB-Hz\n",
                recentTrackedSignals(), recentMaxSnr());
  Serial.printf("GY-271: %s, X=%d Y=%d Z=%d, heading=%.1f true, 3D calibration=%s\n",
                magFresh ? "OK" : "WAIT", magX, magY, magZ, trueHeading,
                calibrated ? "yes" : "no");
  if (calibrating) Serial.println("Calibration: running (10 seconds, all axes)");
  else if (calibrationFailed) Serial.println("Calibration: incomplete; previous settings retained");
  Serial.printf("Magnetic samples rejected: %lu\n", (unsigned long)rejectedMagSamples);
  Serial.printf("GY-521: %s at 0x%02X, accel=(%.3f, %.3f, %.3f)g norm=%.2fg, "
                "pitch=%.1f roll=%.1f, tilt=%s\n",
                accelFresh ? "OK" : "WAIT", imuAddress,
                accelX, accelY, accelZ, accelMagnitudeG,
                pitchDeg, rollDeg, tiltHeadingUsed ? "ON" : "OFF");
  Serial.printf("Display frame: %.1f ms\n", lastFrameDurationUs / 1000.0f);
}

void handleCommand(char *line) {
  while (*line == ' ' || *line == '\t') ++line;
  if (strcasecmp(line, "STATUS") == 0 || *line == '\0') {
    printStatus();
    return;
  }
  if (strcasecmp(line, "NEAREST") == 0) {
    automaticStoreMode = true;
    selectedStore = -1;
    destinationSet = false;
    prefs.putBool("autoStore", true);
    redrawRequested = true;
    Serial.println("Nearest Boulder liquor store mode: waiting for a fresh GPS fix.");
    return;
  }
  if (strcasecmp(line, "STORES") == 0) {
    for (size_t i = 0; i < bottle::STORE_COUNT; ++i)
      Serial.printf("%u: %s / %s / %.7f,%.7f\n", (unsigned)i + 1,
                    bottle::STORES[i].name, bottle::STORES[i].address,
                    bottle::STORES[i].lat, bottle::STORES[i].lon);
    return;
  }
  if (strcasecmp(line, "DETAILS") == 0) {
    forceGpsDiagnostics = !forceGpsDiagnostics;
    redrawRequested = true;
    return;
  }
  if (strcasecmp(line, "CLEAR") == 0) {
    automaticStoreMode = false;
    selectedStore = -1;
    prefs.putBool("autoStore", false);
    destinationSet = false;
    destinationLat = NAN;
    destinationLon = NAN;
    prefs.putBool("set", false);
    redrawRequested = true;
    Serial.println("Destination cleared.");
    return;
  }
  if (strcasecmp(line, "NMEA") == 0) {
    rawNmeaUntilMs = millis() + 5000;
    Serial.println("Raw GPS data for 5 seconds:");
    return;
  }
  if (strcasecmp(line, "CAL") == 0) {
    startCalibration();
    return;
  }
  char *end = nullptr;
  const double lat = strtod(line, &end);
  if (end == line) goto invalid;
  while (*end == ' ' || *end == '\t') ++end;
  if (*end++ != ',') goto invalid;
  {
    char *lonStart = end;
    const double lon = strtod(lonStart, &end);
    if (end == lonStart) goto invalid;
    while (*end == ' ' || *end == '\t') ++end;
    if (*end == '\0' && isfinite(lat) && isfinite(lon) &&
        lat >= -90.0 && lat <= 90.0 && lon >= -180.0 && lon <= 180.0) {
      saveDestination(lat, lon);
      return;
    }
  }
invalid:
  Serial.println("Use decimal degrees: latitude,longitude. Example: 39.739236,-104.990251");
}

void readUsbCommands() {
  while (Serial.available()) {
    const char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (commandOverflow) Serial.println("Command too long.");
      else if (commandLength > 0) {
        commandLine[commandLength] = '\0';
        handleCommand(commandLine);
      }
      commandLength = 0;
      commandOverflow = false;
    } else if (!commandOverflow) {
      if (commandLength + 1 < sizeof(commandLine)) commandLine[commandLength++] = c;
      else commandOverflow = true;
    }
  }
}

void readCalibrationButton(uint32_t now) {
  const bool down = digitalRead(CAL_BUTTON_PIN) == LOW;
  if (down && !calButtonWasDown && now - lastCalButtonMs > 300) {
    lastCalButtonMs = now;
    if (magOk) startCalibration();
  }
  calButtonWasDown = down;
}

float normalizedDegrees(float degreesValue) {
  while (degreesValue < 0.0f) degreesValue += 360.0f;
  while (degreesValue >= 360.0f) degreesValue -= 360.0f;
  return degreesValue;
}





void updateNearestStore(uint32_t now) {
  if (!automaticStoreMode) return;
  const bool fix = gps.location.isValid() && gps.location.age() <= FIX_MAX_AGE_MS;
  if (!fix) {
    selectedStore = -1;
    destinationSet = false;
    return;
  }
  if (selectedStore >= 0 && now - lastNearestUpdateMs < 1000) return;
  lastNearestUpdateMs = now;
  const int best = bottle::nearestStore(gps.location.lat(), gps.location.lng(), fix);
  if (best < 0) { selectedStore = -1; destinationSet = false; return; }
  if (best != selectedStore) {
    Serial.printf("Nearest: %s / %s / %.0f m straight line\n",
                  bottle::STORES[best].name, bottle::STORES[best].address,
                  bottle::distanceMeters(gps.location.lat(), gps.location.lng(), bottle::STORES[best]));
    redrawRequested = true;
  }
  selectedStore = best;
  destinationLat = bottle::STORES[best].lat;
  destinationLon = bottle::STORES[best].lon;
  destinationSet = true;
}

void drawDisplay() {
  const uint32_t frameStartUs = micros();
  const uint32_t now = millis();
  const bool fix = gps.location.isValid() && gps.location.age() <= FIX_MAX_AGE_MS;
  const bool moving = fix && gps.course.isValid() && gps.speed.isValid() &&
                      gps.course.age() <= FIX_MAX_AGE_MS &&
                      gps.speed.age() <= FIX_MAX_AGE_MS &&
                      gps.speed.mps() >= MIN_COURSE_SPEED_MPS;
  const bool headingReady = magFresh || moving;
  const float upBearing = magFresh ? trueHeading : moving ? (float)gps.course.deg() : 0.0f;
  if (headingReady) {
    if (!isfinite(displayHeading)) displayHeading = upBearing;
    const float delta = fmodf(upBearing - displayHeading + 540.0f, 360.0f) - 180.0f;
    displayHeading = normalizedDegrees(displayHeading + 0.45f * delta);
  } else displayHeading = NAN;
  bottleui::State view;
  view.fix = fix; view.lostFix = gps.location.isValid() && !fix;
  view.headingValid = headingReady; view.heading = headingReady ? displayHeading : 0;
  view.magnetic = magFresh; view.tilt = tiltHeadingUsed;
  view.calibrated = calibrated; view.calibrationFailed = calibrationFailed;
  view.calibrating = calibrating; view.details = forceGpsDiagnostics;
  view.automatic = automaticStoreMode; view.store = selectedStore;
  view.target = destinationSet && fix;
  if (view.target) {
    view.distance = TinyGPSPlus::distanceBetween(gps.location.lat(), gps.location.lng(), destinationLat, destinationLon);
    view.bearing = (float)TinyGPSPlus::courseTo(gps.location.lat(), gps.location.lng(), destinationLat, destinationLon);
  }
  view.used = gps.satellites.isValid() && gps.satellites.age() <= FIX_MAX_AGE_MS ? (int)gps.satellites.value() : -1;
  view.view = gpsViewCount(); view.tracked = recentTrackedSignals(); view.snr = recentMaxSnr(); view.quality = gpsQuality();
  view.hdop = gps.hdop.isValid() && gps.hdop.age() <= FIX_MAX_AGE_MS ? gps.hdop.hdop() : NAN;
  view.rx = gpsCharsPerSecond; view.valid = gps.passedChecksum(); view.bad = gps.failedChecksum();
  const uint32_t elapsed = now - calStartMs;
  view.calRemainingMs = calibrating && elapsed < CAL_DURATION_MS ? CAL_DURATION_MS - elapsed : 0;
  bottleui::draw(gfx, view, now);
  if (frame.getBuffer()) {
    tft.startWrite(); tft.setAddrWindow(0, 0, 240, 240);
    tft.writePixels(frame.getBuffer(), 240UL * 240UL); tft.endWrite();
  }
  lastFrameDurationUs = micros() - frameStartUs;
}

void setup() {
  Serial.begin(115200); // In Arduino IDE enable "USB CDC On Boot".
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX, GPS_TX);
  prefs.begin("waypoint", false);
  calibrated = prefs.getUInt("calVersion", 0) == 2;
  if (calibrated || prefs.getBool("magCal", false)) {
    magOffsetX = prefs.getFloat("magOffX", 0);
    magOffsetY = prefs.getFloat("magOffY", 0);
    magScaleX = prefs.getFloat("magScX", 1);
    magScaleY = prefs.getFloat("magScY", 1);
  }
  if (calibrated) {
    magOffsetZ = prefs.getFloat("magOffZ", 0);
    magScaleZ = prefs.getFloat("magScZ", 1);
    magFieldRadius = prefs.getFloat("magRadius", 0);
  }
  automaticStoreMode = prefs.getBool("autoStore", true);
  if (!automaticStoreMode) {
    if (prefs.isKey("set")) {
      if (prefs.getBool("set", false)) {
        const double lat = prefs.getDouble("lat", NAN);
        const double lon = prefs.getDouble("lon", NAN);
        if (isfinite(lat) && isfinite(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
          destinationLat = lat;
          destinationLon = lon;
          destinationSet = true;
        }
      }
    } else if (isfinite(DEFAULT_LAT) && isfinite(DEFAULT_LON)) {
      saveDestination(DEFAULT_LAT, DEFAULT_LON);
    }
  }


  Wire.begin(MAG_SDA, MAG_SCL);
  Wire.setClock(100000);
  pinMode(CAL_BUTTON_PIN, INPUT_PULLUP);
  imuOk = startImu();
  magOk = startMagnetometer();

  if (!SPI.begin(TFT_SCK, -1, TFT_MOSI, -1)) {
    Serial.println("SPI start failed. Check ESP32 board selection.");
  }
  Serial.println("Starting GC9A01A display on hardware SPI SCK=10, MOSI=11, CS=GND, DC=13, RST=3V3");
  tft.begin(16000000);
  tft.setRotation(0);
  tft.fillScreen(RED);
  delay(300);
  tft.fillScreen(GREEN);
  delay(300);
  tft.fillScreen(CYAN);
  delay(300);
  tft.fillScreen(BLACK);
  if (magOk && !calibrated) startCalibration();
  else if (calibrated) Serial.println("3D CAL restored from flash. Press BOOT or send CAL to redo it.");
  else Serial.println("CAL skipped: GY-271 not ready.");
  Serial.println(frame.getBuffer() ? "Display buffer ready" : "Display buffer unavailable; updates may flicker");
  Serial.println("Bottle Radar ready. Commands: NEAREST, STORES, DETAILS, STATUS, NMEA, CAL, CLEAR, or latitude,longitude.");
  printStatus();
  drawDisplay();
  redrawRequested = false;
  lastDrawMs = millis();
}

void loop() {
  while (gpsSerial.available()) {
    const char c = (char)gpsSerial.read();
    if (gps.encode(c)) updateGsvCycle();
    if (millis() < rawNmeaUntilMs) Serial.write(c);
  }
  readUsbCommands();
  const uint32_t now = millis();
  updateNearestStore(now);
  readCalibrationButton(now);
  updateImu(now);
  updateMagnetometer(now);
  if (accelFresh && now - lastAccelSuccessMs > 500) accelFresh = false;
  if (magFresh && now - lastMagSuccessMs > 2000) magFresh = false;
  if (calibrating && now - calStartMs >= CAL_DURATION_MS) finishCalibration();
  updateGpsStats(now);
  const uint32_t period = DRAW_PERIOD_MS; // Keep the GPS sweep animated while searching.
  if (redrawRequested || now - lastDrawMs >= period) {
    lastDrawMs = now;
    drawDisplay();
    redrawRequested = false;
  }
  if (now - lastReportMs >= 5000) {
    printStatus();
    lastReportMs = now;
  }
}
