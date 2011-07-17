#!/usr/bin/python

import cPickle
import geocoder
import sys
import math

# generated by analysis/sf_streets.py
records_cross = cPickle.load(file('/tmp/sf-crossstreets.pickle'))

# generated by analysis/sf_residences.py
records_residences = cPickle.load(file('/tmp/sf-residences.pickle'))

# generated by analysis/sf_freestanding_streets.py
records_free = cPickle.load(file('/tmp/sf-freestanding.pickle'))

records = records_cross + records_residences + records_free

g = geocoder.Geocoder("ABQIAAAAafDALeUVyxhUndZQcT0BRRQjgiEk1Ut90lZbiCSD8tXKcVgrkBQLYOFQ3xwutc5R9SNzfGaKxMnf7g", 5)

def FormatGeocode(x):
  return "%s\t%s -> %d @ %d (%s %f,%f)" % (
      id, addr, x.status, x.accuracy, x.city, x.lat, x.lon)


def Locate(g, id, addr):
  x = g.Locate(addr)
  if x.status != 200:
    print "%s\t%s -> status %d" % (id, addr, x.status)
    return None
  if not InSF(x.lat, x.lon): return None
  return x


def LatLonDistance(lat1, lon1, lat2, lon2):
  """The "haversine" formula."""
  R = 3963  # mi
  dLat = (lat2-lat1) * math.pi / 180.0
  dLon = (lon2-lon1) * math.pi / 180.0
  lat1 = lat1 * math.pi / 180.0
  lat2 = lat2 * math.pi / 180.0

  a = math.sin(dLat/2) * math.sin(dLat/2) + \
      math.sin(dLon/2) * math.sin(dLon/2) * math.cos(lat1) * math.cos(lat2);
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a));
  d = R * c
  return d


def InSF(lat, lon):
  if lat < 37.684907 or lon < -122.517471:  # sw -- in the ocean south of the zoo
    return False
  if lat > 37.833649 or lon > -122.35817:  # ne -- just off the edge of Treasure Island
    return False
  return True


def GetAverageLatLon(lat_lons):
  # compute all-pairs distances. They should all be tightly clustered, say
  # within half a mile. For reference, Folsom&4th to Folsom&5th is 0.17 miles.
  ds = []
  for i in range(len(lat_lons)):
    for j in range(i + 1, len(lat_lons)):
      ds.append(LatLonDistance(lat_lons[i][0], lat_lons[i][1], lat_lons[j][0], lat_lons[j][1]))

  d = max(ds)
  if d > 0.5: return None

  lat = 0.0
  lon = 0.0
  for xlat, xlon in lat_lons:
    lat += xlat
    lon += xlon
  lat /= len(lat_lons)
  lon /= len(lat_lons)
  return (lat, lon)


# These intersections/streets have changed names since the photos were taken.
fixes = {
  '13th and howard': '13th and south van ness',
  '14th and howard': '14th and south van ness',
  '15th and howard': '15th and south van ness',
  '16th and howard': '16th and south van ness',
  '17th and howard': '17th and south van ness',
  '18th and howard': '18th and south van ness',
  'eighteenth and howard': '18th and south van ness',
  '19th and howard': '19th and south van ness',
  '20th and howard': '20th and south van ness',
  '21st and howard': '21st and south van ness',
  '22nd and howard': '22nd and south van ness',
  '23rd and howard': '23rd and south van ness',
  '24th and howard': '24th and south van ness',
  '25th and howard': '25th and south van ness',
  
  'castro and market': 'castro street and market street',  # this is strange!
  'california and market': 'spear street and market street',
  'market and post': '2nd street and market street',
  'embarcadero and market': 'Harry Bridges Plaza',
  'sloat and sunset': 'Cunard Cruise Line',
  'eddy and market': '@37.784724,-122.407715',
  'eddy and powell': '@37.784724,-122.407715'
}
  

pairs = []  # (street1, street2) -- in alphabetical order!
addresses = []  # e.g. 7142 market street
tinies = []  # e.g. Balance street
for rec in records:
  id, street1, cross = rec
  if not cross: continue

  # first check for an address
  addy = [x for x in cross if x.startswith("address:")]
  if addy:
    assert 1 == len(addy)
    loc_str = addy[0].replace("address:", "")
    x = Locate(g, id, loc_str)
    if not x or x.accuracy != 8:
      sys.stderr.write('Failure: %s -> %s\n' % (addy[0], x))
    else:
      print '%s\t%f,%f\t%s' % (id, x.lat, x.lon, loc_str)
    continue

  # ... or a block
  block = [x for x in cross if x.startswith("block:")]
  if block:
    assert 1 == len(block)
    b = int(block[0].split(":")[1])
    assert 0 == b % 100
    loc_str = str(b + 50) + ' ' + street1
    x = Locate(g, id, loc_str)
    if not x or x.accuracy != 8:
      sys.stderr.write('Failure: %s -> %s\n' % (addy[0], x))
    else:
      print '%s\t%f,%f\t%s' % (id, x.lat, x.lon, loc_str)
    continue

  # next check if it's just a tiny
  if len(cross) == 1 and cross[0].startswith("tiny:"):
    loc = cross[0].replace('tiny:', '')
    x = Locate(g, id, loc)
    if not x or x.accuracy != 6:
      sys.stderr.write('Failure: %s -> %s\n' % (loc, x))
    else:
      print '%s\t%f,%f\t%s' % (id, x.lat, x.lon, loc)
    continue

  lat_lons = []
  loc_strs = []
  for c_street in [c for c in cross if not c.startswith("tiny:")]:
    pair = [c_street, street1]
    pair.sort()
    locatable = ' and '.join(pair)
    # a few special cases for streets that were renamed or intersections that
    # no longer exist.
    take_it = False
    if locatable in fixes:
      locatable = fixes[locatable]
      if 'and' not in locatable: take_it = True

    locatable = locatable.replace('army', 'cesar chavez')
    if locatable[0] != '@':
      x = Locate(g, id, locatable)
    else:
      ll = locatable[1:].split(',')
      x = geocoder.FakeLocation(float(ll[0]), float(ll[1]), 7)

    if not x or (x.accuracy != 7 and not take_it):
      sys.stderr.write('Failure: %s -> %s\n' % (locatable, x))
    else:
      lat_lons.append((x.lat, x.lon))
      loc_strs.append(locatable)

  if len(lat_lons) == 1:
    print '%s\t%f,%f\t%s' % (id, lat_lons[0][0], lat_lons[0][1], loc_strs[0])
  elif len(lat_lons) > 0:
    # TODO(danvk): check for important strings like "between"
    lat_lon = GetAverageLatLon(lat_lons)
    if lat_lon:
      print '%s\t%f,%f\t%s' % (id, lat_lon[0], lat_lon[1], ','.join(loc_strs))
  else:
    # these are geocode failures
    pass

