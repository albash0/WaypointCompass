#pragma once
#include <cmath>
#include "BoulderStores.h"

namespace bottle {
constexpr double EARTH_RADIUS_M = 6371000.0;
constexpr double RADIANS_PER_DEGREE = 0.017453292519943295;

inline bool validLocation(double lat, double lon) {
  return std::isfinite(lat) && std::isfinite(lon) &&
         lat >= -90.0 && lat <= 90.0 && lon >= -180.0 && lon <= 180.0;
}

inline double distanceMeters(double lat, double lon, const Store &store) {
  const double dlat = (store.lat - lat) * RADIANS_PER_DEGREE;
  const double dlon = (store.lon - lon) * RADIANS_PER_DEGREE;
  const double a = std::sin(dlat / 2) * std::sin(dlat / 2) +
                   std::cos(lat * RADIANS_PER_DEGREE) *
                   std::cos(store.lat * RADIANS_PER_DEGREE) *
                   std::sin(dlon / 2) * std::sin(dlon / 2);
  const double bounded = a < 0 ? 0 : a > 1 ? 1 : a;
  return 2 * EARTH_RADIUS_M * std::atan2(std::sqrt(bounded), std::sqrt(1 - bounded));
}

// A missing/stale GPS fix must never select a destination using default (0,0).
inline int nearestStore(double lat, double lon, bool freshFix) {
  if (!freshFix || !validLocation(lat, lon)) return -1;
  int nearest = -1;
  double bestDistance = HUGE_VAL;
  for (size_t i = 0; i < STORE_COUNT; ++i) {
    const double distance = distanceMeters(lat, lon, STORES[i]);
    if (distance < bestDistance) {
      bestDistance = distance;
      nearest = static_cast<int>(i);
    }
  }
  return nearest;
}
} // namespace bottle
