#pragma once
#include <Adafruit_GFX.h>
#include <cmath>
#include <cstdio>
#include <cstring>
#include "BottleNavigation.h"

namespace bottleui {
constexpr uint16_t rgb(int r, int g, int b) { return ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3); }
constexpr uint16_t BG = rgb(7, 13, 25), GRID = rgb(24, 43, 57);
constexpr uint16_t INK = rgb(235, 244, 241), MUTED = rgb(133, 163, 175);
constexpr uint16_t MINT = rgb(73, 244, 188), GOLD = rgb(255, 193, 76);
constexpr uint16_t PINK = rgb(255, 104, 143), DIM = rgb(23, 79, 73);
constexpr uint16_t PURPLE = rgb(157, 126, 255);
struct State {
  bool fix = false, lostFix = false, headingValid = false, magnetic = false;
  bool tilt = false, calibrated = false, calibrationFailed = false;
  bool calibrating = false, details = false, automatic = true, target = false;
  float heading = 0, bearing = 0;
  double distance = 0;
  float hdop = NAN;
  int store = -1, used = -1, view = -1, tracked = -1, snr = -1, quality = -1;
  uint32_t rx = 0, valid = 0, bad = 0, calRemainingMs = 0;
};
inline float wrap(float angle) {
  while (angle < 0) angle += 360;
  while (angle >= 360) angle -= 360;
  return angle;
}
inline void point(float angle, float radius, int16_t &x, int16_t &y) {
  const float radians = angle * 0.017453292519943295f;
  x = (int16_t)std::lround(120 + std::sin(radians) * radius);
  y = (int16_t)std::lround(119 - std::cos(radians) * radius);
}
inline void text(Adafruit_GFX &g, const char *label, int y, int size, uint16_t color) {
  g.setTextWrap(false); g.setTextSize(size); g.setTextColor(color);
  int16_t x1, y1; uint16_t w, h;
  g.getTextBounds(label, 0, 0, &x1, &y1, &w, &h);
  g.setCursor((240 - (int)w) / 2, y); g.print(label);
}
inline void fittedText(Adafruit_GFX &g, const char *label, int y, int maxWidth = 150) {
  if (std::strlen(label) * 12 <= (size_t)maxWidth) { text(g, label, y, 2, INK); return; }
  char clipped[40]; std::snprintf(clipped, sizeof(clipped), "%s", label);
  const size_t maxChars = (size_t)maxWidth / 6;
  if (std::strlen(clipped) > maxChars && maxChars >= 3) {
    clipped[maxChars - 3] = '.'; clipped[maxChars - 2] = '.';
    clipped[maxChars - 1] = '.'; clipped[maxChars] = '\0';
  }
  text(g, clipped, y, 1, INK);
}
inline void sparkle(Adafruit_GFX &g, int x, int y, int size, uint16_t color) {
  g.drawFastHLine(x - size, y, 2 * size + 1, color);
  g.drawFastVLine(x, y - size, 2 * size + 1, color);
}
inline void bottleIcon(Adafruit_GFX &g, int x, int y, int w, int h, uint16_t color, float fill) {
  const int neckW = w / 3, neckH = h / 4, bodyY = y + neckH;
  const int neckX = x + (w - neckW) / 2;
  g.fillRoundRect(x, bodyY, w, h - neckH, w / 6, DIM);
  const int liquidH = (int)((h - neckH - 4) * fill);
  if (liquidH > 0) g.fillRect(x + 2, y + h - 2 - liquidH, w - 4, liquidH, color);
  g.drawRoundRect(x, bodyY, w, h - neckH, w / 6, color);
  g.drawRect(neckX, y, neckW, neckH + 1, color);
  g.fillRoundRect(neckX - 2, y - 3, neckW + 4, 4, 1, GOLD);
  if (w > 20) { g.fillRoundRect(x + w / 4, bodyY + (h - neckH) / 3, w / 2, h / 5, 2, BG); }
}
inline void rim(Adafruit_GFX &g, float heading, bool headingValid) {
  g.drawCircle(120, 119, 117, GRID);
  for (int d = 0; d < 360; d += 15) {
    int16_t x1, y1, x2, y2;
    point(wrap(d - heading), d % 90 == 0 ? 100 : d % 30 == 0 ? 111 : 114, x1, y1);
    point(wrap(d - heading), 116, x2, y2);
    g.drawLine(x1, y1, x2, y2, d == 0 && headingValid ? PINK : GRID);
  }
  const char *labels[] = {"N", "E", "S", "W"};
  for (int i = 0; headingValid && i < 4; ++i) {
    int16_t x, y; point(wrap(i * 90 - heading), 112, x, y);
    g.setTextSize(1); g.setTextColor(i == 0 ? PINK : MUTED);
    g.setCursor(x - 3, y - 4); g.print(labels[i]);
  }
  g.fillTriangle(120, 15, 116, 21, 124, 21, MINT);
}
inline void header(Adafruit_GFX &g, bool fix) {
  text(g, "BOTTLE RADAR", 24, 1, GOLD);
  bottleIcon(g, 72, 21, 5, 11, MINT, .5f);
  g.fillCircle(166, 27, 2, fix ? MINT : GOLD);
}
inline void arrow(Adafruit_GFX &g, float angle) {
  int16_t tx, ty, lx, ly, rx, ry, bx, by, sx, sy;
  point(angle, 43, tx, ty); point(angle - 96, 18, lx, ly);
  point(angle + 96, 18, rx, ry); point(angle + 180, 22, bx, by);
  point(angle, 8, sx, sy);
  g.fillTriangle(tx + 2, ty + 3, lx + 2, ly + 3, bx + 2, by + 3, DIM);
  g.fillTriangle(tx + 2, ty + 3, rx + 2, ry + 3, bx + 2, by + 3, DIM);
  g.fillTriangle(tx, ty, lx, ly, bx, by, MINT);
  g.fillTriangle(tx, ty, rx, ry, bx, by, GOLD);
  g.drawLine(tx, ty, sx, sy, INK);
  g.fillCircle(120, 119, 3, BG);
}
inline void diagnostics(Adafruit_GFX &g, const State &s) {
  text(g, "THE NERDY DETAILS", 42, 1, MINT);
  char line[48];
  text(g, s.fix ? "GPS LOCKED" : "NO GPS FIX", 59, 2, s.fix ? MINT : GOLD);
  std::snprintf(line, sizeof(line), "RX %lu chars/s", (unsigned long)s.rx); text(g, line, 85, 1, INK);
  std::snprintf(line, sizeof(line), "NMEA %lu OK / %lu BAD", (unsigned long)s.valid, (unsigned long)s.bad); text(g, line, 102, 1, INK);
  std::snprintf(line, sizeof(line), "SAT VIEW %d  TRACK %d", s.view, s.tracked); text(g, line, 119, 1, INK);
  std::snprintf(line, sizeof(line), "USED %d  FIX %d  SNR %d", s.used, s.quality, s.snr); text(g, line, 136, 1, INK);
  if (std::isfinite(s.hdop)) std::snprintf(line, sizeof(line), "HDOP %.1f  UP %lum", s.hdop, (unsigned long)(millis() / 60000UL));
  else std::snprintf(line, sizeof(line), "HDOP --  UP %lum", (unsigned long)(millis() / 60000UL));
  text(g, line, 151, 1, MUTED);
  text(g, s.magnetic ? (s.tilt ? "TILT ON / MAG OK" : "MAG OK / KEEP LEVEL") : "MAG WAIT / CHECK CAL", 163, 1, s.magnetic ? MINT : PINK);
  text(g, s.calibrationFailed ? "CAL RETRY" : s.calibrated ? "3D CAL SAVED" : "CAL NEEDED", 181, 1, MUTED);
  text(g, "DETAILS = BACK", 204, 1, MUTED);
}
inline void calibration(Adafruit_GFX &g, const State &s, uint32_t now) {
  text(g, "A LITTLE BOTTLE MAGIC", 46, 1, INK);
  const float done = 1.0f - (s.calRemainingMs > 10000 ? 10000 : s.calRemainingMs) / 10000.0f;
  for (int i = 0; i < (int)(done * 60); ++i) {
    int16_t x1, y1, x2, y2; point(i * 6, 112, x1, y1); point(i * 6, 115, x2, y2);
    g.drawLine(x1, y1, x2, y2, GOLD);
  }
  bottleIcon(g, 99, 76, 42, 72, MINT, done);
  sparkle(g, 88, 92, 3 + (now / 250) % 2, GOLD);
  sparkle(g, 154, 116, 3, PURPLE);
  char line[24]; std::snprintf(line, sizeof(line), "%lu SEC", (unsigned long)((s.calRemainingMs + 999) / 1000));
  text(g, line, 161, 2, GOLD);
  text(g, "ROLL / PITCH / TURN", 187, 1, INK);
  text(g, "SAVED WHEN COMPLETE", 204, 1, MUTED);
}
inline void searching(Adafruit_GFX &g, const State &s, uint32_t now) {
  text(g, s.lostFix ? "GPS SIGNAL LOST" : "SEARCHING THE SKY", 43, 1, INK);
  const float sweep = (now % 7200) / 20.0f;
  int16_t px, py;
  for (int d = 0; d < 28; d += 2) { point(sweep - d, 53, px, py); g.drawLine(120, 119, px, py, d < 6 ? DIM : rgb(12, 35, 38)); }
  for (int radius : {18, 36, 54}) g.drawCircle(120, 119, radius, GRID);
  g.drawFastHLine(66, 119, 109, GRID); g.drawFastVLine(120, 65, 109, GRID);
  point(sweep, 53, px, py); g.drawLine(120, 119, px, py, MINT); g.fillCircle(px, py, 2, MINT);
  bottleIcon(g, 112, 104, 16, 30, GOLD, .5f);
  char line[40]; if (s.automatic) std::snprintf(line, sizeof(line), "%u STORES READY", (unsigned)bottle::STORE_COUNT);
  else std::snprintf(line, sizeof(line), "WAYPOINT MODE");
  text(g, line, 180, 1, GOLD);
  std::snprintf(line, sizeof(line), "SAT %d  VIEW %d  RX %lu", s.used, s.view, (unsigned long)s.rx); text(g, line, 195, 1, MUTED);
  text(g, s.rx == 0 && now > 5000 ? "CHECK GPS WIRING" : !s.headingValid ? "CAL / CHECK MAG" : "TAKE ME OUTSIDE", 209, 1, INK);
}
inline void navigation(Adafruit_GFX &g, const State &s, uint32_t now) {
  const char *name = s.store >= 0 ? bottle::STORES[s.store].name : "YOUR WAYPOINT";
  fittedText(g, name, 42, 144);
  const float relative = wrap(s.bearing - (s.headingValid ? s.heading : 0));
  const bool close = s.distance <= 25.0;
  // Leave the lower arc open for the turn cue and distance.
  for (int d = -128; d < 128; d += 2) {
    int16_t x1, y1, x2, y2;
    point(d, 58, x1, y1); point(d + 2, 58, x2, y2); g.drawLine(x1, y1, x2, y2, GRID);
    point(d, 61, x1, y1); point(d + 2, 61, x2, y2); g.drawLine(x1, y1, x2, y2, DIM);
  }
  if (close) {
    bottleIcon(g, 104, 87, 32, 61, GOLD, .7f);
    for (int i = 0; i < 7; ++i) { int16_t x, y; point((int)((i * 37 + (now / 80) % 240) % 240) - 120, 43 + i % 3 * 4, x, y); sparkle(g, x, y, i % 2 + 1, i % 2 ? PURPLE : MINT); }
    text(g, "FOUND IT!", 158, 1, GOLD);
  } else {
    arrow(g, relative);
    const float turn = relative > 180 ? relative - 360 : relative;
    char guide[32];
    if (!s.headingValid) std::snprintf(guide, sizeof(guide), "NORTH UP / ALIGN TOP N");
    else if (std::fabs(turn) < 12) std::snprintf(guide, sizeof(guide), "STRAIGHT AHEAD");
    else std::snprintf(guide, sizeof(guide), "%s %03d", turn > 0 ? "RIGHT" : "LEFT", (int)std::lround(std::fabs(turn)));
    text(g, guide, 158, 1, s.headingValid ? MINT : PINK);
  }
  char distance[24];
  if (s.distance < 1000) std::snprintf(distance, sizeof(distance), "%.0f m", s.distance);
  else if (s.distance < 100000) std::snprintf(distance, sizeof(distance), "%.1f km", s.distance / 1000);
  else std::snprintf(distance, sizeof(distance), "%.0f km", s.distance / 1000);
  text(g, distance, 173, 3, INK);
  text(g, "STRAIGHT-LINE DISTANCE", 201, 1, MUTED);
  const char *mode = s.calibrationFailed ? "CAL RETRY" : s.magnetic ? (s.tilt ? "GPS / TILT ON" : "GPS / MAG UP") : s.headingValid ? "GPS COURSE UP" : "MAG WAIT / CAL";
  text(g, mode, 211, 1, s.magnetic ? MINT : GOLD);
}
inline void draw(Adafruit_GFX &g, const State &s, uint32_t now) {
  g.fillScreen(BG); g.setTextWrap(false);
  rim(g, s.headingValid ? s.heading : 0, s.headingValid); header(g, s.fix);
  if (s.calibrating) calibration(g, s, now);
  else if (s.details) diagnostics(g, s);
  else if (!s.fix) searching(g, s, now);
  else if (s.target) navigation(g, s, now);
  else { bottleIcon(g, 104, 83, 32, 60, GOLD, .5f); text(g, "NO DESTINATION", 163, 1, INK); text(g, "USB: NEAREST", 186, 1, MINT); }
}
} // namespace bottleui
