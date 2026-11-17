#include "../BottleNavigation.h"
#include <cassert>
#include <cstdio>
#include <cstring>

int main() {
  using namespace bottle;
  assert(STORE_COUNT == 19);
  for (size_t i = 0; i < STORE_COUNT; ++i) {
    assert(validLocation(STORES[i].lat, STORES[i].lon));
    assert(nearestStore(STORES[i].lat, STORES[i].lon, true) == (int)i);
    assert(distanceMeters(STORES[i].lat, STORES[i].lon, STORES[i]) < .01);
  }
  // Use the public city GIS point to check the Williams Village target.
  int selected = nearestStore(STORES[18].lat, STORES[18].lon, true);
  assert(selected == 18);
  selected = nearestStore(40.048, -105.282, true);
  assert(selected >= 0 && std::strcmp(STORES[selected].name, "North Boulder Liquor") == 0);
  assert(nearestStore(40.02, -105.26, false) == -1);
  assert(nearestStore(NAN, -105.26, true) == -1);
  assert(nearestStore(40, INFINITY, true) == -1);
  assert(nearestStore(91, -105, true) == -1);
  assert(nearestStore(40, 181, true) == -1);
  Store east = {"test", "", 0, 1};
  assert(std::fabs(distanceMeters(0, 0, east) - 111194.927) < 1);
  Store dateline = {"test", "", 0, -179.9};
  assert(std::fabs(distanceMeters(0, 179.9, dateline) - 22238.985) < 1);
  Store antipode = {"test", "", 0, 180};
  assert(std::isfinite(distanceMeters(0, 0, antipode)));
  std::puts("Navigation: 19 store locations, nearest selection, stale/invalid fixes, distance edge cases passed.");
}
