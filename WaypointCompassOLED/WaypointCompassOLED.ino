#include <Arduino.h>
#include <Wire.h>
#include <Preferences.h>
#include <TinyGPS++.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

// Pins verified on this ESP32-S3 SuperMini by scanning the connected hardware.
constexpr int MAG_SDA = 8;
constexpr int MAG_SCL = 9;
constexpr int OLED_SDA = 11;
constexpr int OLED_SCL = 10;
constexpr int GPS_RX = 44; // ESP32 RX <- GPS TX
constexpr int GPS_TX = 43; // ESP32 TX -> GPS RX

constexpr uint8_t MAG_ADDRESS = 0x2C;  // QMC5883P on this GY-271
constexpr uint8_t OLED_ADDRESS = 0x3C; // 128x64 SSD1306 OLED
constexpr uint32_t GPS_BAUD = 9600;
constexpr uint32_t GPS_FIX_MAX_AGE_MS = 5000;
constexpr uint32_t CAL_DURATION_MS = 30000;
constexpr double DEFAULT_LAT = NAN;
constexpr double DEFAULT_LON = NAN;
// Approximate true-north correction near the saved Boulder destination (2026).
// Update this value if using the compass far from this area.
constexpr float DECLINATION_DEG = 7.7f;
// Zero means the GY-271 board's +X direction is the front of the device.
// Change after checking the assembled case against a known direction.
constexpr float MOUNT_OFFSET_DEG = 0.0f;

TwoWire oledWire(1);
Adafruit_SSD1306 display(128, 64, &oledWire, -1);
HardwareSerial gpsSerial(1);
TinyGPSPlus gps;
Preferences prefs;

bool oledOk = false;
bool magOk = false;
bool magFresh = false;
bool calibrated = false;
bool calibrating = false;
uint32_t lastMagMs = 0;
uint32_t lastDrawMs = 0;
uint32_t lastReportMs = 0;
uint32_t lastGpsCountMs = 0;
uint32_t lastGpsChars = 0;
uint32_t gpsCharsPerSecond = 0;
uint32_t calStartMs = 0;
int16_t magX = 0, magY = 0, magZ = 0;
int16_t minX = INT16_MAX, maxX = INT16_MIN;
int16_t minY = INT16_MAX, maxY = INT16_MIN;
float offsetX = 0, offsetY = 0;
float scaleX = 1, scaleY = 1;
float trueHeading = NAN;
double destinationLat = DEFAULT_LAT;
double destinationLon = DEFAULT_LON;
bool destinationSet = false;
char commandLine[72] = {};
size_t commandLength = 0;

float wrap360(float angle) {
  while (angle < 0) angle += 360;
  while (angle >= 360) angle -= 360;
  return angle;
}

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

bool startMagnetometer() {
  uint8_t id = 0;
  if (!readMag(0x00, &id, 1) || id != 0x80) {
    Serial.printf("GY-271: expected QMC5883P ID 0x80; got 0x%02X\n", id);
    return false;
  }
  // QST QMC5883P datasheet normal mode setup.
  const bool ok = writeMag(0x29, 0x06) && // axis signs
                  writeMag(0x0B, 0x08) && // set/reset on, +/-8 G
                  writeMag(0x0A, 0xC5);  // normal mode, 50 Hz
  Serial.printf("GY-271 QMC5883P: %s (I2C 0x2C)\n", ok ? "ready" : "init failed");
  return ok;
}

void finishCalibration() {
  calibrating = false;
  const int32_t rangeX = (int32_t)maxX - minX;
  const int32_t rangeY = (int32_t)maxY - minY;
  if (rangeX < 400 || rangeY < 400) {
    Serial.println("CAL failed: rotate the whole device through a full circle, then try again.");
    return;
  }
  offsetX = ((float)maxX + minX) * 0.5f;
  offsetY = ((float)maxY + minY) * 0.5f;
  const float averageRange = ((float)rangeX + rangeY) * 0.5f;
  scaleX = averageRange / rangeX;
  scaleY = averageRange / rangeY;
  calibrated = true;
  prefs.putFloat("magOffX", offsetX);
  prefs.putFloat("magOffY", offsetY);
  prefs.putFloat("magScX", scaleX);
  prefs.putFloat("magScY", scaleY);
  prefs.putBool("magCal", true);
  Serial.printf("CAL saved: X off %.1f scale %.3f, Y off %.1f scale %.3f\n",
                offsetX, scaleX, offsetY, scaleY);
}

void updateMagnetometer(uint32_t now) {
  if (!magOk || now - lastMagMs < 50) return;
  lastMagMs = now;
  uint8_t status = 0;
  if (!readMag(0x09, &status, 1) || !(status & 1) || (status & 2)) return;
  uint8_t data[6];
  if (!readMag(0x01, data, 6)) return;
  magX = (int16_t)((data[1] << 8) | data[0]);
  magY = (int16_t)((data[3] << 8) | data[2]);
  magZ = (int16_t)((data[5] << 8) | data[4]);
  magFresh = true;
  if (calibrating) {
    if (magX < minX) minX = magX;
    if (magX > maxX) maxX = magX;
    if (magY < minY) minY = magY;
    if (magY > maxY) maxY = magY;
  }
  const float x = (magX - offsetX) * scaleX;
  const float y = (magY - offsetY) * scaleY;
  trueHeading = wrap360(atan2f(y, x) * 180.0f / PI +
                        DECLINATION_DEG + MOUNT_OFFSET_DEG);
}

void printStatus() {
  Serial.printf("MAG %s: X=%d Y=%d Z=%d heading=%.1f true, cal=%s\n",
                magFresh ? "OK" : "WAIT", magX, magY, magZ,
                trueHeading, calibrated ? "yes" : "no");
  Serial.printf("GPS: %lu chars/s, %lu valid sentences, %lu bad, %ld satellites, fix=%s\n",
                gpsCharsPerSecond, gps.passedChecksum(), gps.failedChecksum(),
                gps.satellites.isValid() ? (long)gps.satellites.value() : -1L,
                gps.location.isValid() && gps.location.age() < GPS_FIX_MAX_AGE_MS ? "yes" : "no");
  if (destinationSet)
    Serial.printf("Destination: %.7f, %.7f\n", destinationLat, destinationLon);
  else
    Serial.println("Destination: unset");
}

void handleCommand(char *line) {
  while (*line == ' ' || *line == '\t') ++line;
  if (!*line || strcasecmp(line, "STATUS") == 0) {
    printStatus();
    return;
  }
  if (strcasecmp(line, "CAL") == 0) {
    minX = minY = INT16_MAX;
    maxX = maxY = INT16_MIN;
    calStartMs = millis();
    calibrating = true;
    Serial.println("CAL started: rotate the whole device slowly through 360 degrees for 30 seconds.");
    return;
  }
  if (strcasecmp(line, "CLEAR") == 0) {
    destinationSet = false;
    prefs.putBool("set", false);
    Serial.println("Destination cleared.");
    return;
  }
  char *end = nullptr;
  const double lat = strtod(line, &end);
  if (end != line) {
    while (*end == ' ' || *end == '\t') ++end;
    if (*end == ',') {
      char *startLon = ++end;
      const double lon = strtod(startLon, &end);
      while (*end == ' ' || *end == '\t') ++end;
      if (end != startLon && *end == '\0' && isfinite(lat) && isfinite(lon) &&
          lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        destinationLat = lat;
        destinationLon = lon;
        destinationSet = true;
        prefs.putDouble("lat", lat);
        prefs.putDouble("lon", lon);
        prefs.putBool("set", true);
        Serial.printf("Destination saved: %.7f, %.7f\n", lat, lon);
        return;
      }
    }
  }
  Serial.println("Use STATUS, CAL, CLEAR, or latitude,longitude.");
}

void readCommands() {
  while (Serial.available()) {
    const char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (commandLength) {
        commandLine[commandLength] = '\0';
        handleCommand(commandLine);
      }
      commandLength = 0;
    } else if (commandLength + 1 < sizeof(commandLine)) {
      commandLine[commandLength++] = c;
    }
  }
}

void drawPointer(float angle, int16_t cx, int16_t cy, int16_t radius) {
  const float radians = angle * PI / 180.0f;
  const int16_t tipX = cx + lroundf(sinf(radians) * radius);
  const int16_t tipY = cy - lroundf(cosf(radians) * radius);
  const int16_t tailX = cx - lroundf(sinf(radians) * 6);
  const int16_t tailY = cy + lroundf(cosf(radians) * 6);
  display.drawLine(tailX, tailY, tipX, tipY, SSD1306_WHITE);
  display.fillCircle(tipX, tipY, 2, SSD1306_WHITE);
  display.fillCircle(cx, cy, 2, SSD1306_WHITE);
}

void drawDisplay(uint32_t now) {
  if (!oledOk) return;
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  const bool fix = gps.location.isValid() && gps.location.age() < GPS_FIX_MAX_AGE_MS;
  if (!magOk) display.print("MAG ERROR");
  else if (!magFresh) display.print("MAG WAIT");
  else display.print("MAG OK");
  display.setCursor(72, 0);
  if (fix) display.printf("GPS %lu", gps.satellites.isValid() ? gps.satellites.value() : 0UL);
  else if (gpsCharsPerSecond == 0) display.print("GPS NO RX");
  else display.print("GPS WAIT");
  display.drawLine(0, 9, 127, 9, SSD1306_WHITE);

  if (calibrating) {
    display.setCursor(0, 17);
    display.println("CALIBRATING COMPASS");
    display.println("Rotate whole device");
    display.println("slowly in a circle.");
    display.printf("%lu seconds left", (CAL_DURATION_MS - (now - calStartMs)) / 1000UL);
  } else {
    display.drawCircle(29, 36, 22, SSD1306_WHITE);
    display.drawLine(29, 11, 29, 15, SSD1306_WHITE); // device forward
    if (magFresh) {
      float angle = -trueHeading; // north relative to the device
      if (fix && destinationSet) {
        const float target = TinyGPSPlus::courseTo(gps.location.lat(), gps.location.lng(),
                                                    destinationLat, destinationLon);
        angle = wrap360(target - trueHeading);
      }
      drawPointer(angle, 29, 36, 18);
    }
    display.setCursor(60, 14);
    if (magFresh) display.printf("HDG %03d", (int)lroundf(trueHeading) % 360);
    else display.print("HDG ---");
    display.setCursor(60, 27);
    if (fix && destinationSet) {
      const double distance = TinyGPSPlus::distanceBetween(gps.location.lat(), gps.location.lng(),
                                                            destinationLat, destinationLon);
      if (distance < 1000) display.printf("TO %.0fm", distance);
      else display.printf("TO %.1fkm", distance / 1000.0);
      display.setCursor(60, 40);
      display.print(distance <= 15 ? "ARRIVED" : "ARROW: GO");
    } else if (!destinationSet) {
      display.print("SET DEST");
      display.setCursor(60, 40);
      display.print("ARROW: N");
    } else {
      display.printf("SAT %ld", gps.satellites.isValid() ? (long)gps.satellites.value() : -1L);
      display.setCursor(60, 40);
      display.print("ARROW: N");
    }
    display.setCursor(0, 57);
    display.print(calibrated ? "CAL OK" : "CAL NEEDED: USB CAL");
  }
  display.display();
}

void setup() {
  Serial.begin(115200);
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX, GPS_TX);
  prefs.begin("waypoint", false);
  if (prefs.getBool("set", true)) {
    destinationLat = prefs.getDouble("lat", DEFAULT_LAT);
    destinationLon = prefs.getDouble("lon", DEFAULT_LON);
  } else {
    destinationSet = false;
  }
  calibrated = prefs.getBool("magCal", false);
  if (calibrated) {
    offsetX = prefs.getFloat("magOffX", 0);
    offsetY = prefs.getFloat("magOffY", 0);
    scaleX = prefs.getFloat("magScX", 1);
    scaleY = prefs.getFloat("magScY", 1);
  }
  Wire.begin(MAG_SDA, MAG_SCL);
  Wire.setClock(100000);
  oledWire.begin(OLED_SDA, OLED_SCL);
  oledWire.setClock(100000);
  oledOk = display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS);
  magOk = startMagnetometer();
  Serial.printf("OLED: %s on SDA=%d SCL=%d address 0x%02X\n",
                oledOk ? "ready" : "not found", OLED_SDA, OLED_SCL, OLED_ADDRESS);
  Serial.println("Waypoint compass: STATUS, CAL, CLEAR, or latitude,longitude.");
  printStatus();
  drawDisplay(millis());
}

void loop() {
  while (gpsSerial.available()) gps.encode((char)gpsSerial.read());
  readCommands();
  const uint32_t now = millis();
  updateMagnetometer(now);
  if (calibrating && now - calStartMs >= CAL_DURATION_MS) finishCalibration();
  if (now - lastGpsCountMs >= 1000) {
    gpsCharsPerSecond = gps.charsProcessed() - lastGpsChars;
    lastGpsChars = gps.charsProcessed();
    lastGpsCountMs = now;
  }
  if (now - lastDrawMs >= 250) {
    drawDisplay(now);
    lastDrawMs = now;
  }
  if (now - lastReportMs >= 5000) {
    printStatus();
    lastReportMs = now;
  }
}
