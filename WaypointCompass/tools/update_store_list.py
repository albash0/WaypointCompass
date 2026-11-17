"""Regenerate offline destinations from the City of Boulder's public GIS query.
Usage: python3 tools/update_store_list.py [path-to-downloaded-query.json]
No board location is sent to the server. The request contains only a license type.
"""
import json, sys, urllib.parse, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'https://gis.bouldercolorado.gov/ags_svr1/rest/services/plan/LiquorLicenses/MapServer/0/query'
PARAMS = {'where': "LICTYPE = 'Retail Liquor Store' AND STATUS = 1", 'outFields': '*', 'returnGeometry': 'true', 'outSR': '4326', 'f': 'json'}
URL = ENDPOINT + '?' + urllib.parse.urlencode(PARAMS)
if len(sys.argv) > 1:
    data = json.loads(Path(sys.argv[1]).read_text())
else:
    with urllib.request.urlopen(URL, timeout=30) as response:
        data = json.load(response)
if 'error' in data or data.get('exceededTransferLimit'):
    raise RuntimeError('Incomplete city GIS response: ' + str(data.get('error', 'pagination required')))
short_names = {754:'Boulder Beer & Liquor',759:'Williams Village',763:'Boulder Wine Merchant',771:'Gunbarrel Liquor',772:'B Town Wine & Spirits',809:'West End Wine Shop',813:'Persona Wine',815:'Boulder Wine & Spirits',819:"Bailey's Wine & Spirits",860:'Harvest Wine & Spirits',864:'A-OK Liquor',879:"Pettyjohn's",898:"Hazel's",911:'North Boulder Liquor',930:'Broadway Wine & Spirits',931:'Baseline Liquor',932:'Whole Foods Wine',947:'Rose Hill Wine & Spirits',984:'Sundry Wine N Liquor'}
rows=[]
for feature in data['features']:
    a=feature['attributes']; g=feature.get('geometry')
    if a['LICTYPE']!='Retail Liquor Store' or a['STATUS']!=1:continue
    if not g or not (39.9<g['y']<40.15 and -105.4<g['x']<-105.1):
        raise ValueError('Missing or invalid local coordinate: '+str(a))
    rows.append({'city_object_id':a['OBJECTID'],'name':a['TRADENAME'],'label':short_names.get(a['OBJECTID'],a['TRADENAME'].title()),'address':a['LOCATION'],'latitude':g['y'],'longitude':g['x']})
rows.sort(key=lambda r:r['name'].casefold())
assert rows, 'Refusing to replace store list with an empty response'
as_of=datetime.now(ZoneInfo('America/Denver')).date().isoformat()
snapshot={'retrieved':as_of,'source':'City of Boulder Liquor Licenses GIS','source_url':URL,'notes':'Retail Liquor Store, STATUS=1. Snapshot only; no opening-hours or live closure data. Coordinates are city map points, not surveyed entrances.','stores':rows}
(ROOT/'data'/'boulder-stores.json').write_text(json.dumps(snapshot,indent=2)+'\n')
(ROOT/'CompactPCB'/'firmware'/'store-data.json').write_text(json.dumps(snapshot,indent=2)+'\n')
header='''#pragma once
#include <cstddef>
namespace bottle {
struct Store { const char *name; const char *address; double lat; double lon; };
// City of Boulder public liquor-license map, SNAPSHOT_DATE snapshot.
// Retail Liquor Store / STATUS=1. See data/boulder-stores.json for provenance.
// Locations are map points, not entrance surveys. No live opening hours.
constexpr Store STORES[] = {
'''
header=header.replace('SNAPSHOT_DATE', as_of)
for r in rows:header+='  {'+json.dumps(r['label'])+', '+json.dumps(r['address'])+f', {r["latitude"]:.8f}, {r["longitude"]:.8f}'+'},\n'
header+='};\nconstexpr size_t STORE_COUNT = sizeof(STORES) / sizeof(STORES[0]);\n} // namespace bottle\n'
for d in [ROOT,ROOT/'CompactPCB'/'firmware'/'WaypointCompassCompact']:(d/'BoulderStores.h').write_text(header)
print(f'Generated {len(rows)} city-listed retail liquor-store destinations.')
