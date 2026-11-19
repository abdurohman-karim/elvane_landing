#!/usr/bin/env python3
"""
Builds the landing's data from the real Elvane data in the backend repository:

  * public/data/terrain.bin   — Big Chimgan elevation grid (uint16 metres) from the region pack's
                                 Copernicus DEM (terrarium tiles, z12), for contours and the cursor readout
  * src/data/terrain.json     — grid size and corners
  * src/data/route.json       — the fastest way up Big Chimgan along OSM trails from the end of the
                                 road (Dijkstra over the region's trail graph, the same data the app routes on)
  * src/data/silhouette.json  — a cross-section of the peak for the altitude slider
  * src/data/pois.json        — springs, passes, huts and camps around the route
  * src/data/peaks.json       — the 26 catalog peaks
  * src/data/regions.json     — the 7 offline regions: polygons, areas and pack sizes
  * src/data/stats.json       — totals over all region packs

Usage: python3 scripts/build-data.py [path to elvane_backend]
"""
import heapq
import io
import json
import math
import os
import sqlite3
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '..', 'elvane_backend'))
OUT = os.path.join(BACKEND, 'tools', 'tiles', 'out')
PACK = os.path.join(OUT, 'west-tianshan', 'pack')
SRC_DATA = os.path.join(ROOT, 'src', 'data')
PUB_DATA = os.path.join(ROOT, 'public', 'data')
for d in (SRC_DATA, PUB_DATA):
    os.makedirs(d, exist_ok=True)

SUMMIT = (41.49519, 70.05867, 3309)  # Big Chimgan, catalog
Z = 12


def write_json(name, value):
    with open(os.path.join(SRC_DATA, name), 'w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, separators=(',', ':'))


# ---------------------------------------------------------------- web mercator

def lonlat_to_px(lon, lat, z=Z):
    n = 256 * 2 ** z
    x = (lon + 180) / 360 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def px_to_lonlat(x, y, z=Z):
    n = 256 * 2 ** z
    lon = x / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon, lat


def haversine(a, b):
    r = 6371000
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- terrain

def load_dem(px0, py0, px1, py1):
    """Stitches z12 terrarium tiles covering the mercator pixel box; returns metres as float32."""
    db = sqlite3.connect(os.path.join(PACK, 'terrain.mbtiles'))
    tx0, ty0, tx1, ty1 = int(px0 // 256), int(py0 // 256), int(px1 // 256), int(py1 // 256)
    w, h = (tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256
    dem = np.zeros((h, w), dtype=np.float32)
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            tms_y = 2 ** Z - 1 - ty
            row = db.execute('select tile_data from tiles where zoom_level=? and tile_column=? and tile_row=?',
                             (Z, tx, tms_y)).fetchone()
            if not row:
                raise SystemExit(f'missing terrain tile {Z}/{tx}/{ty}')
            rgb = np.asarray(Image.open(io.BytesIO(row[0])).convert('RGB'), dtype=np.float32)
            ele = rgb[:, :, 0] * 256 + rgb[:, :, 1] + rgb[:, :, 2] / 256 - 32768
            dem[(ty - ty0) * 256:(ty - ty0 + 1) * 256, (tx - tx0) * 256:(tx - tx0 + 1) * 256] = ele
    return dem, tx0 * 256, ty0 * 256


def sample(dem, ox, oy, x, y):
    """Bilinear elevation at a mercator pixel."""
    fx, fy = x - ox, y - oy
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    dx, dy = fx - x0, fy - y0
    a = dem[y0, x0] * (1 - dx) + dem[y0, x0 + 1] * dx
    b = dem[y0 + 1, x0] * (1 - dx) + dem[y0 + 1, x0 + 1] * dx
    return float(a * (1 - dy) + b * dy)


# ---------------------------------------------------------------- route

def decode_polyline(s, precision=5):
    coords, index, lat, lon = [], 0, 0, 0
    factor = 10 ** precision
    while index < len(s):
        for which in (0, 1):
            shift, result = 0, 0
            while True:
                b = ord(s[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            d = ~(result >> 1) if result & 1 else result >> 1
            if which == 0:
                lat += d
            else:
                lon += d
        coords.append((lat / factor, lon / factor))
    return coords


ROADS = {'unclassified', 'tertiary', 'secondary', 'primary', 'residential', 'living_street',
         'primary_link', 'secondary_link', 'tertiary_link'}


def find_route():
    db = sqlite3.connect(os.path.join(PACK, 'region.sqlite'))
    box = (SUMMIT[1] - 0.15, SUMMIT[1] + 0.15, SUMMIT[0] - 0.12, SUMMIT[0] + 0.12)
    ids = [r[0] for r in db.execute(
        'select id from edges_rtree where max_lon>=? and min_lon<=? and max_lat>=? and min_lat<=?', box)]
    edges = {}
    for chunk in range(0, len(ids), 900):
        part = ids[chunk:chunk + 900]
        q = f'select id,a,b,length_m,class,difficulty,time_fwd_s,time_back_s,polyline from edges where id in ({",".join("?" * len(part))})'
        for row in db.execute(q, part):
            edges[row[0]] = row
    nodes = {}
    for row in db.execute('select id,lat,lon,ele from nodes where lon between ? and ? and lat between ? and ?', box):
        nodes[row[0]] = row
    adj = {}
    road_nodes = set()
    for eid, a, b, length, cls, diff, tf, tb, poly in edges.values():
        adj.setdefault(a, []).append((b, eid, tf))  # travel a -> b
        adj.setdefault(b, []).append((a, eid, tb))
        if cls in ROADS:
            road_nodes.update((a, b))
    # Summit: the trail node closest to the catalog point
    top = min((n for n in nodes.values() if n[0] in adj), key=lambda n: haversine((n[1], n[2]), SUMMIT[:2]))
    print(f'  summit node {top[0]} at {haversine((top[1], top[2]), SUMMIT[:2]):.0f} m from the catalog point')
    # Reverse Dijkstra from the summit: the cost of reaching the summit *from* each node, uphill
    radj = {}
    for u, lst in adj.items():
        for v, eid, t in lst:
            radj.setdefault(v, []).append((u, eid, t))  # going u -> v costs t
    dist, prev = {top[0]: 0.0}, {}
    heap = [(0.0, top[0])]
    best = None
    while heap:
        d, v = heapq.heappop(heap)
        if d > dist.get(v, 1e18):
            continue
        if v in road_nodes and v != top[0]:
            best = v
            break
        for u, eid, t in radj.get(v, []):
            e = edges[eid]
            if e[5] > 4:  # the classic way up is T4 near the top; nothing harder
                continue
            nd = d + t
            if nd < dist.get(u, 1e18):
                dist[u] = nd
                prev[u] = (v, eid)
                heapq.heappush(heap, (nd, u))
    if best is None:
        raise SystemExit('no route to the summit')
    # Walk from the road end up to the summit, concatenating edge polylines in travel direction
    pts, diffs, classes = [], [], []
    cur = best
    while cur != top[0]:
        nxt, eid = prev[cur]
        e = edges[eid]
        line = decode_polyline(e[8])
        if e[1] != cur:  # edge stored b -> a
            line = line[::-1]
        if pts:
            line = line[1:]
        pts.extend(line)
        diffs.extend([e[5]] * len(line))
        classes.append(e[4])
        cur = nxt
    print(f'  road end node {best}: {len(pts)} points, {dist[best] / 3600:.2f} h by the graph, classes {sorted(set(classes))}')
    # Off-trail tail to the catalog summit if the graph stops short
    gap = haversine(pts[-1], SUMMIT[:2])
    if gap > 15:
        pts.append(SUMMIT[:2])
        diffs.append(diffs[-1])
    return pts, diffs, dist[best], db


def resample(pts, step):
    """Points every `step` metres along a polyline of (lat, lon)."""
    out = [pts[0]]
    acc = 0.0
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        seg = haversine(a, b)
        while acc + seg >= step and seg > 0:
            t = (step - acc) / seg
            a = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            out.append(a)
            seg = haversine(a, b)
            acc = 0.0
        acc += seg
    out.append(pts[-1])
    return out


def tobler_hours(dist_m, rise_m):
    slope = rise_m / dist_m if dist_m else 0
    kmh = 6 * math.exp(-3.5 * abs(slope + 0.05))
    return dist_m / 1000 / kmh


# ---------------------------------------------------------------- main

def main():
    print('route…')
    route, diffs, graph_s, region_db = find_route()

    # Terrain box around the route, 16:10, with margin, in mercator pixels
    xs, ys = zip(*(lonlat_to_px(p[1], p[0]) for p in route))
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span_x = max(max(xs) - min(xs), (max(ys) - min(ys)) * 1.6) * 1.55
    span_y = span_x / 1.6
    px0, py0, px1, py1 = cx - span_x / 2, cy - span_y / 2, cx + span_x / 2, cy + span_y / 2
    dem, ox, oy = load_dem(px0 - 2, py0 - 2, px1 + 2, py1 + 2)

    # Grid: GW x GH samples over the box
    GW = 360
    GH = round(GW / 1.6)
    grid = np.zeros((GH, GW), dtype=np.float32)
    for j in range(GH):
        y = py0 + (py1 - py0) * j / (GH - 1)
        for i in range(GW):
            x = px0 + (px1 - px0) * i / (GW - 1)
            grid[j, i] = sample(dem, ox, oy, x, y)
    # Light smoothing for calm contours (3x3 box, twice)
    for _ in range(2):
        p = np.pad(grid, 1, mode='edge')
        grid = sum(p[dy:dy + GH, dx:dx + GW] for dy in range(3) for dx in range(3)) / 9
    grid_u16 = np.clip(np.round(grid), 0, 65535).astype('<u2')
    grid_u16.tofile(os.path.join(PUB_DATA, 'terrain.bin'))
    nw, se = px_to_lonlat(px0, py0), px_to_lonlat(px1, py1)
    write_json('terrain.json', {
        'w': GW, 'h': GH, 'min': int(grid_u16.min()), 'max': int(grid_u16.max()),
        'nw': [round(nw[0], 6), round(nw[1], 6)], 'se': [round(se[0], 6), round(se[1], 6)],
        'mercator': {'z': Z, 'x0': px0, 'y0': py0, 'x1': px1, 'y1': py1},
        'attribution': 'Copernicus DEM GLO-30',
    })
    print(f'  terrain {GW}x{GH}, {grid_u16.min()}–{grid_u16.max()} m, box {nw} – {se}')

    def to_grid(lat, lon):
        x, y = lonlat_to_px(lon, lat)
        return (x - px0) / (px1 - px0) * (GW - 1), (y - py0) / (py1 - py0) * (GH - 1)

    # Route samples every 25 m with elevations from the DEM
    pts = resample(route, 25)
    out, dist_acc, up, down, hours = [], 0.0, 0.0, 0.0, 0.0
    prev = None
    eles = []
    for lat, lon in pts:
        x, y = lonlat_to_px(lon, lat)
        eles.append(sample(dem, ox, oy, x, y))
    # Smooth the profile so the ascent does not count DEM noise
    k = 5
    smooth = [sum(eles[max(0, i - k):i + k + 1]) / len(eles[max(0, i - k):i + k + 1]) for i in range(len(eles))]
    for idx, (lat, lon) in enumerate(pts):
        ele = smooth[idx]
        if prev is not None:
            d = haversine(prev[0], (lat, lon))
            rise = ele - prev[1]
            dist_acc += d
            up += max(rise, 0)
            down += max(-rise, 0)
            hours += tobler_hours(d, rise)
        gx, gy = to_grid(lat, lon)
        out.append([round(gx, 2), round(gy, 2), round(ele), round(dist_acc), round(lat, 5), round(lon, 5)])
        prev = ((lat, lon), ele)
    # Difficulty along the way, as fractions of the route
    write_json('route.json', {
        'points': out,  # [gridX, gridY, ele, distM, lat, lon]
        'lengthM': round(dist_acc), 'ascentM': round(up), 'descentM': round(down),
        'hoursUp': round(hours, 2), 'graphHours': round(graph_s / 3600, 2),
        'maxDifficulty': max(diffs), 'start': {'lat': round(route[0][0], 5), 'lon': round(route[0][1], 5), 'ele': round(smooth[0])},
    })
    print(f'  route {dist_acc / 1000:.1f} km, +{up:.0f} / -{down:.0f} m, {hours:.1f} h (Tobler), T{max(diffs)}, start {smooth[0]:.0f} m')

    # Silhouette: the cross-section through the summit that looks most like a mountain
    sx, sy = lonlat_to_px(SUMMIT[1], SUMMIT[0])
    best = None
    for az in range(0, 180, 5):
        a = math.radians(az)
        prof = []
        for t in np.linspace(-1, 1, 161):
            x = sx + math.cos(a) * t * 180
            y = sy + math.sin(a) * t * 180
            if ox + 1 < x < ox + dem.shape[1] - 2 and oy + 1 < y < oy + dem.shape[0] - 2:
                prof.append(sample(dem, ox, oy, x, y))
        if len(prof) < 161:
            continue
        score = max(prof) - (prof[0] + prof[-1]) / 2
        if best is None or score > best[0]:
            best = (score, az, prof)
    _, az, prof = best
    write_json('silhouette.json', {'azimuth': az, 'widthM': round(360 * 29.3 * math.cos(math.radians(SUMMIT[0]))),
                                   'ele': [round(v) for v in prof]})
    print(f'  silhouette azimuth {az}, {min(prof):.0f}–{max(prof):.0f} m')

    # POIs in the terrain box
    nwl, sel = nw, se
    pois = []
    for kind, name, name_ru, name_en, ele, lat, lon in region_db.execute(
            "select kind,name,name_ru,name_en,ele,lat,lon from poi where kind in ('spring','pass','hut','shelter','camp','waterfall','peak','viewpoint') "
            'and lon between ? and ? and lat between ? and ?', (nwl[0], sel[0], sel[1], nwl[1])):
        gx, gy = to_grid(lat, lon)
        pois.append({'k': kind, 'n': name_ru or name or name_en, 'en': name_en or name, 'e': ele,
                     'x': round(gx, 1), 'y': round(gy, 1)})
    write_json('pois.json', pois)
    print(f'  {len(pois)} POIs in the box')

    # Regions with pack sizes and totals over the packs
    regs = json.load(open(os.path.join(BACKEND, 'tools', 'tiles', 'regions.json'), encoding='utf-8'))['regions']
    stats = {'springs': 0, 'passes': 0, 'peaks': 0, 'camps': 0, 'huts': 0, 'waterfalls': 0, 'pathsKm': 0, 'graphKm': 0, 'packsMb': 0}
    out_regs = []
    for r in regs:
        pack = os.path.join(OUT, r['id'], 'pack')
        manifest = json.load(open(os.path.join(pack, 'manifest.json')))
        db = sqlite3.connect(os.path.join(pack, 'region.sqlite'))
        counts = dict(db.execute('select kind,count(*) from poi group by kind').fetchall())
        km = db.execute('select sum(length_m)/1000 from edges').fetchone()[0]
        paths = db.execute("select sum(length_m)/1000 from edges where class in ('path','footway','bridleway','steps','track')").fetchone()[0]
        stats['springs'] += counts.get('spring', 0)
        stats['passes'] += counts.get('pass', 0)
        stats['peaks'] += counts.get('peak', 0)
        stats['camps'] += counts.get('camp', 0)
        stats['huts'] += counts.get('hut', 0) + counts.get('shelter', 0)
        stats['waterfalls'] += counts.get('waterfall', 0)
        stats['graphKm'] += km
        stats['pathsKm'] += paths
        stats['packsMb'] += manifest['size'] / 1024 / 1024
        out_regs.append({'id': r['id'], 'name': r['name'], 'areas': r['areas'], 'polygon': r['polygon'],
                         'mb': round(manifest['size'] / 1024 / 1024, 1), 'springs': counts.get('spring', 0),
                         'passes': counts.get('pass', 0), 'peaks': counts.get('peak', 0), 'km': round(km)})
    stats = {k: round(v) for k, v in stats.items()}
    write_json('regions.json', out_regs)
    write_json('stats.json', stats)
    print(f'  regions: {stats}')


if __name__ == '__main__':
    main()
