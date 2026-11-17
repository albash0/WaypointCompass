#pragma once
#include <cstddef>
namespace bottle {
struct Store { const char *name; const char *address; double lat; double lon; };
// City of Boulder public liquor-license map, 2026-10-16 snapshot.
// Retail Liquor Store / STATUS=1. See data/boulder-stores.json for provenance.
// Locations are map points, not entrance surveys. No live opening hours.
constexpr Store STORES[] = {
  {"A-OK Liquor", "2690 28th St, Unit A", 40.02707749, -105.25759262},
  {"B Town Wine & Spirits", "5360 Arapahoe Ave, Suite C", 40.01393641, -105.22782447},
  {"Bailey's Wine & Spirits", "4800 Baseline Rd, Unit E-101", 39.99832428, -105.23541601},
  {"Baseline Liquor", "2750 Baseline Rd", 39.99948606, -105.25912855},
  {"Boulder Beer & Liquor", "4700 Table Mesa Dr", 39.98460393, -105.23916360},
  {"Boulder Wine & Spirits", "3325 28th St, Unit 3", 40.03551208, -105.25989860},
  {"Boulder Wine Merchant", "2690 Broadway", 40.02533798, -105.28116612},
  {"Broadway Wine & Spirits", "2550 Baseline Rd", 39.99874666, -105.26161561},
  {"Gunbarrel Liquor", "6566 Lookout Rd", 40.07221868, -105.20064410},
  {"Harvest Wine & Spirits", "3075 Arapahoe Ave, Unit A", 40.01514824, -105.25199550},
  {"Hazel's", "1955 28th St", 40.02088380, -105.25983372},
  {"North Boulder Liquor", "3990 N Broadway", 40.04754427, -105.28183172},
  {"Persona Wine", "2299 Pearl St, Suite 6", 40.02108154, -105.26592631},
  {"Pettyjohn's", "613 S Broadway", 39.98443191, -105.25006792},
  {"Rose Hill Wine & Spirits", "1089 13th St", 40.00714420, -105.27640658},
  {"Sundry Wine N Liquor", "3303 Bluff St, Suite RS-2", 40.02787237, -105.25041523},
  {"West End Wine Shop", "777 Pearl St, Unit C", 40.01687968, -105.28554431},
  {"Whole Foods Wine", "2315 30th St", 40.02399258, -105.25522123},
  {"Williams Village", "655 30th St", 39.99897610, -105.25361538},
};
constexpr size_t STORE_COUNT = sizeof(STORES) / sizeof(STORES[0]);
} // namespace bottle
