#!/usr/bin/env python3
"""Dependency-free demo backend for the Bengaluru Safe Route Finder prototype."""
from __future__ import annotations

import csv, heapq, json, math, os, random, re, threading
from collections import defaultdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = Path(os.getenv("GRAPHML_PATH", ROOT / "data/roads.graphml"))
LIGHT_PATH = Path(os.getenv("STREETLIGHT_CSV", ROOT / "data/streetlights.csv"))
CRIME_DATA_PATH = Path(os.getenv("CRIME_DATA_CSV", ROOT / "data/crime_districts.csv"))
MAX_NODES = int(os.getenv("MAX_PILOT_NODES", "60000"))
LIGHT_RADIUS_M = 35.0
POLICE_THRESHOLD_KM = 1.5
POLICE_DECAY_KM = 2.0
DAY_START_HOUR = 7
DAY_END_HOUR = 21

FLAG_CATALOG = {
    "poor_lighting": {"id":"poor_lighting", "title":"Lighting information unavailable", "category":"infrastructure", "description":"Lighting has not been verified for this road segment.", "source":"lighting_data"},
    "distant_police": {"id":"distant_police", "title":"Police station farther away", "category":"emergency_access", "description":"The nearest mapped police station is beyond the configured distance threshold.", "source":"police_station_data"},
    "isolated_road": {"id":"isolated_road", "title":"Limited route information", "category":"route_conditions", "description":"Information about activity and available assistance on this road is limited.", "source":"route_data"},
}

# Demo stations are intentionally labelled as reference points, not live emergency data.
POLICE_STATIONS = [
    (13.0350, 77.5240, "Pilot police reference - west"),
    (13.0550, 77.5150, "Pilot police reference - central"),
    (13.0750, 77.5320, "Pilot police reference - north"),
]


def haversine(a, b):
    lat1, lon1 = a; lat2, lon2 = b
    p = math.pi / 180
    x = (lon2-lon1) * p * math.cos((lat1+lat2)*p/2)
    y = (lat2-lat1) * p
    return 6371000 * math.sqrt(x*x+y*y)


def parse_value(value):
    value = (value or "").strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1].strip(" '\"")
    try: return float(value)
    except ValueError: return value


def first_attr(data, name, default=None):
    value = data.get(name, default)
    if isinstance(value, str) and value.startswith("["):
        return value.strip("[] '") .split("'")[0]
    return value


def time_safety_factor(value=None):
    """Return a safety multiplier for the requested local departure time."""
    if value:
        try:
            hour = datetime.strptime(value, "%H:%M").hour
        except ValueError:
            raise ValueError("departure_time must use HH:MM format")
    else:
        hour = datetime.now().hour
    if DAY_START_HOUR <= hour < DAY_END_HOUR:
        return 1.0
    if 21 <= hour < 23:
        return 0.92
    if hour >= 23 or hour < 4:
        return 0.78
    return 0.88


def traveller_safety_factor(value=1):
    """Return a capped group-safety benefit with diminishing returns."""
    try:
        travellers = int(value)
    except (TypeError, ValueError):
        raise ValueError("travellers must be a whole number between 1 and 20")
    if travellers < 1 or travellers > 20:
        raise ValueError("travellers must be a whole number between 1 and 20")
    return min(0.45, 0.15 * math.log2(travellers))


class Store:
    def __init__(self):
        self.nodes = {}
        self.adj = defaultdict(list)
        self.lights = []
        self.crime_records = []
        self.max_crime_total = 1
        self.grid = defaultdict(list)
        self.lock = threading.RLock()
        self.bounds = self._load_lights()
        self._load_crime_data()
        self._load_graph()
        self._score_edges()

    def _load_crime_data(self):
        if not CRIME_DATA_PATH.exists():
            return
        with CRIME_DATA_PATH.open(newline="", encoding="utf-8-sig") as f:
            rows = csv.DictReader(f)
            rng = random.Random(20261010)
            for row in rows:
                district = (row.get("Districts") or "").strip()
                if not district or district.lower().startswith("total"):
                    continue
                try:
                    ipc = int(row["IPC Cases"])
                    sll = int(row["SLL Cases"])
                    total = int(row["Total"])
                except (KeyError, TypeError, ValueError):
                    continue
                lat = rng.uniform(self.bounds[0], self.bounds[1])
                lon = rng.uniform(self.bounds[2], self.bounds[3])
                self.crime_records.append({
                    "district": district,
                    "ipc_cases": ipc,
                    "sll_cases": sll,
                    "total_cases": total,
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                })
        self.max_crime_total = max((x["total_cases"] for x in self.crime_records), default=1)

    def crime_rate_for_point(self, point):
        """Normalize the uploaded district total into a comparable 1-85 index."""
        if not self.crime_records:
            return 1
        record = min(
            self.crime_records,
            key=lambda x: haversine(point, (x["lat"], x["lon"])),
        )
        return max(1, round(record["total_cases"] / self.max_crime_total * 85, 1))

    def _load_lights(self):
        with LIGHT_PATH.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.lights = [(float(r["latitude"]), float(r["longitude"])) for r in rows]
        lats = [x[0] for x in self.lights]; lons = [x[1] for x in self.lights]
        return (min(lats), max(lats), min(lons), max(lons))

    def _load_graph(self):
        ns = "{http://graphml.graphdrawing.org/xmlns}"
        keys = {}
        for event, elem in ET.iterparse(GRAPH_PATH, events=("start", "end")):
            if event == "start" and elem.tag == ns + "key":
                keys[elem.attrib["id"]] = elem.attrib.get("attr.name", elem.attrib["id"])
            if event == "end" and elem.tag == ns + "node":
                d = {keys.get(x.attrib.get("key"), x.attrib.get("key")): parse_value(x.text) for x in elem.findall(ns+"data")}
                if "x" in d and "y" in d:
                    lat, lon = float(d["y"]), float(d["x"])
                    if self.bounds[0] <= lat <= self.bounds[1] and self.bounds[2] <= lon <= self.bounds[3]:
                        self.nodes[elem.attrib["id"]] = (lat, lon)
                elem.clear()
            if event == "end" and elem.tag == ns + "edge":
                src, dst = elem.attrib["source"], elem.attrib["target"]
                if src in self.nodes and dst in self.nodes:
                    d = {keys.get(x.attrib.get("key"), x.attrib.get("key")): parse_value(x.text) for x in elem.findall(ns+"data")}
                    length = float(d.get("length", haversine(self.nodes[src], self.nodes[dst])))
                    road = str(d.get("highway", "unknown"))
                    edge = {"u":src, "v":dst, "length":length, "road_type":road, "geometry":[self.nodes[src], self.nodes[dst]]}
                    self.adj[src].append(edge)
                elem.clear()
        if not self.nodes or not self.adj:
            raise RuntimeError("No graph data loaded. Check GRAPHML_PATH and the pilot bounds.")
        if len(self.nodes) > MAX_NODES:
            # Keep the reference data bounded for a laptop demo; nearest pilot nodes are retained.
            keep = set(sorted(self.nodes, key=lambda n: (self.nodes[n][0], self.nodes[n][1]))[:MAX_NODES])
            self.nodes = {k:v for k,v in self.nodes.items() if k in keep}
            self.adj = defaultdict(list, {u:[e for e in es if e["v"] in keep] for u,es in self.adj.items() if u in keep})

    def _grid_key(self, point):
        return (int(point[0]*1000), int(point[1]*1000))

    def _score_edges(self):
        for point in self.lights:
            self.grid[self._grid_key(point)].append(point)
        for edges in self.adj.values():
            for e in edges:
                mid = ((e["geometry"][0][0]+e["geometry"][1][0])/2, (e["geometry"][0][1]+e["geometry"][1][1])/2)
                nearby = []
                gx, gy = self._grid_key(mid)
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        nearby.extend(self.grid.get((gx+dx,gy+dy), []))
                distances = sorted(haversine(mid, x) for x in nearby)
                e["light_distance_m"] = distances[0] if distances else None
                e["light_count"] = sum(d <= LIGHT_RADIUS_M for d in distances)
                e["lighting_status"] = "verified" if e["light_count"] else "unverified"
                e["lighting_score"] = min(1.0, e["light_count"] / max(e["length"] / 100, 1))
                e["police_distance_km"] = min(haversine(mid, (x,y)) for x,y,_ in POLICE_STATIONS) / 1000
                # Police proximity is a positive safety factor. It decays smoothly
                # with distance instead of becoming relevant only after a threshold.
                e["police_safety"] = math.exp(-e["police_distance_km"] / POLICE_DECAY_KM)
                e["crime_rate_pct"] = self.crime_rate_for_point(mid)
                crime_risk = e["crime_rate_pct"] / 85.0
                e["risk"] = (
                    0.30 * (1 - e["lighting_score"])
                    + 0.30 * (1 - e["police_safety"])
                    + 0.40 * crime_risk
                )

    def nearest(self, point):
        node, distance = min(((n, haversine(point, p)) for n,p in self.nodes.items()), key=lambda x:x[1])
        return node

    def route(self, origin, destination, mode, departure_time=None, travellers=1, avoid_edges=None):
        start, goal = self.nearest(origin), self.nearest(destination)
        alpha = {"fastest":0.35, "balanced":1.6, "safest":5.0}[mode]
        avoid_edges = avoid_edges or set()
        time_factor = time_safety_factor(departure_time)
        group_benefit = traveller_safety_factor(travellers)
        dist = {start:0.0}; prev = {}; heap=[(0.0,start)]
        while heap:
            cost,u=heapq.heappop(heap)
            if cost != dist.get(u): continue
            if u == goal: break
            for e in self.adj.get(u, []):
                time_risk = (1 - (1 - e["risk"]) * time_factor) * (1 - group_benefit)
                overlap_penalty = e["length"] * (3.5 if mode == "balanced" else 6.0) if (e["u"], e["v"]) in avoid_edges else 0
                weight=e["length"]*(1 + alpha*time_risk) + overlap_penalty
                nxt=e["v"]; new=cost+weight
                if new < dist.get(nxt,float("inf")):
                    dist[nxt]=new; prev[nxt]=(u,e); heapq.heappush(heap,(new,nxt))
        if goal not in prev and goal != start: raise ValueError("No connected route found in the pilot area")
        edges=[]; n=goal
        while n != start:
            p,e=prev[n]; edges.append(e); n=p
        edges.reverse()
        return self._format_route(mode, edges, departure_time, time_factor, travellers, group_benefit), {(e["u"], e["v"]) for e in edges}

    def _format_route(self, mode, edges, departure_time, time_factor, travellers, group_benefit):
        distance=sum(e["length"] for e in edges); light=sum(e["length"] for e in edges if e["lighting_status"]=="verified")
        average_risk=sum(e["length"]*(1 - (1-e["risk"])*time_factor) for e in edges)/max(distance,1)
        # Keep 50 as a neutral baseline: incomplete lighting data should not
        # make an urban route look catastrophically unsafe by itself.
        score=max(0, min(100, 50 + 50*(1 - average_risk*(1 - group_benefit))))
        police_safety=sum(e["length"]*e["police_safety"] for e in edges)/max(distance,1)
        crime_rate=sum(e["length"]*e["crime_rate_pct"] for e in edges)/max(distance,1)
        police=min((e["police_distance_km"] for e in edges), default=0)
        flags=[]
        if any(e["lighting_status"]=="unverified" for e in edges): flags.append(dict(FLAG_CATALOG["poor_lighting"]))
        if any(e["police_distance_km"]>POLICE_THRESHOLD_KM for e in edges): flags.append(dict(FLAG_CATALOG["distant_police"]))
        if len(edges) < 2: flags.append(dict(FLAG_CATALOG["isolated_road"]))
        coords=[]
        for i,e in enumerate(edges):
            if i==0: coords.append(e["geometry"][0])
            coords.append(e["geometry"][1])
        return {"id":mode,"distance_m":round(distance,1),"walking_minutes":round(distance/5000*60,1),"safety_score":round(score,1),"lighting_verified_pct":round(light/max(distance,1)*100,1),"police_safety_pct":round(police_safety*100,1),"nearest_police_km":round(police,2),"crime_rate_pct":round(crime_rate,1),"departure_time":departure_time or datetime.now().strftime("%H:%M"),"time_safety_factor":time_factor,"travellers":travellers,"traveller_safety_benefit_pct":round(group_benefit*100,1),"flags":flags,"geometry":{"type":"LineString","coordinates":[[p[1],p[0]] for p in coords]},"data_confidence":"real streetlight CSV + uploaded district crime totals + reference police points"}

    def map_data(self):
        features=[]
        for u,edges in self.adj.items():
            for e in edges:
                if e["u"] > e["v"]: continue
                features.append({"type":"Feature","geometry":{"type":"LineString","coordinates":[[p[1],p[0]] for p in e["geometry"]]},"properties":{"lighting_status":e["lighting_status"],"lighting_score":round(e["lighting_score"],2),"police_distance_km":round(e["police_distance_km"],2),"police_safety":round(e["police_safety"],2),"crime_rate_pct":e["crime_rate_pct"],"risk":round(e["risk"],2)}})
                if len(features)>=3000: return {"type":"FeatureCollection","features":features}
        return {"type":"FeatureCollection","features":features}

STORE = None
class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200):
        body=json.dumps(payload).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(body)
    def do_OPTIONS(self): self.send_response(204); self.send_header("Access-Control-Allow-Origin","*"); self.send_header("Access-Control-Allow-Headers","Content-Type"); self.end_headers()
    def do_GET(self):
        path=urlparse(self.path).path
        try:
            if path == "/frontend/index.html":
                body=(ROOT / "frontend/index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path=="/api/health": return self._send({"status":"ok","nodes":len(STORE.nodes),"streetlights":len(STORE.lights)})
            if path=="/api/map": return self._send(STORE.map_data())
            if path=="/api/stations": return self._send({"synthetic":True,"stations":[{"name":n,"lat":lat,"lon":lon} for lat,lon,n in POLICE_STATIONS]})
            if path=="/api/crime-data": return self._send({"simulated_locations":True,"source":CRIME_DATA_PATH.name,"records":STORE.crime_records})
            if path=="/": return self._send({"service":"Safe Route Finder"})
            return self._send({"error":"not_found"},404)
        except Exception as exc: return self._send({"error":str(exc)},500)
    def do_POST(self):
        if urlparse(self.path).path != "/api/route": return self._send({"error":"not_found"},404)
        try:
            n=int(self.headers.get("Content-Length",0)); data=json.loads(self.rfile.read(n))
            origin=(float(data["origin"]["lat"]),float(data["origin"]["lon"])); destination=(float(data["destination"]["lat"]),float(data["destination"]["lon"]))
            departure_time=data.get("departure_time")
            travellers=data.get("travellers", 1)
            time_factor=time_safety_factor(departure_time)
            group_benefit=traveller_safety_factor(travellers)
            fastest, fastest_edges = STORE.route(origin, destination, "fastest", departure_time, travellers)
            balanced, balanced_edges = STORE.route(origin, destination, "balanced", departure_time, travellers, fastest_edges)
            safest, safest_edges = STORE.route(origin, destination, "safest", departure_time, travellers, fastest_edges | balanced_edges)
            routes=[fastest, balanced, safest]
            recommended=max(routes,key=lambda r:r["safety_score"] - 0.15*r["walking_minutes"])
            return self._send({"routes":routes,"recommended_route":recommended["id"],"time_safety_factor":time_factor,"travellers":travellers,"traveller_safety_benefit_pct":round(group_benefit*100,1),"explanation":f"{recommended['id'].title()} is recommended for {routes[0]['departure_time']} with {travellers} traveller(s) and a safety score of {recommended['safety_score']}/100. Group size provides a capped, diminishing safety benefit; it does not guarantee safety.","assumptions":["Streetlight absence is a data-quality signal, not proof that a road is dark.","Police locations are synthetic reference points for the prototype and must be replaced with verified data before deployment.","No route-distance constraint is applied; the selected route is evaluated on its full path."]})
        except (KeyError,ValueError) as exc: return self._send({"error":str(exc)},400)
        except Exception as exc: return self._send({"error":str(exc)},500)

if __name__ == "__main__":
    print("Loading pilot graph and streetlights...")
    STORE=Store(); print(f"Loaded {len(STORE.nodes)} nodes, {sum(map(len,STORE.adj.values()))} directed edges, {len(STORE.lights)} lights")
    ThreadingHTTPServer(("127.0.0.1", int(os.getenv("PORT","8000"))), Handler).serve_forever()
