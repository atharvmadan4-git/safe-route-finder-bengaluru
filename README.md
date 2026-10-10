# Safe Route Finder — Bengaluru hackathon prototype

An interactive hackathon prototype that compares fastest, balanced, and safety-weighted walking routes. It uses the supplied Bengaluru GraphML road network and 24k-row streetlight CSV as pilot reference data.

See [`HACKATHON_SUBMISSION.md`](HACKATHON_SUBMISSION.md) for the pitch,
demo flow, judging criteria, and responsible-use notes. See
[`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) for a two-minute presentation script.

## What is implemented

- Interactive Leaflet map with route comparison.
- Separate name-based origin and destination search fields with Bengaluru pilot reference locations. Selecting a result applies it to that endpoint; clicking the map sets the destination.
- Real supplied streetlight coordinates used to mark road segments as `verified` when a light is within 35 m of the segment midpoint.
- **Absence of a nearby streetlight is intentionally represented as `unverified`, not as proof of darkness or a crime risk.** The UI displays this as a data-quality/infrastructure flag.
- Police proximity is now the stronger safety factor: route segments receive a smooth positive proximity score that is highest near a police reference point and decays with distance. Segments beyond 1.5 km still receive a `distant_police` informational flag.
- Fastest, balanced, and safest routes with distance, time, safety score, lighting coverage, police distance, and explanatory flags.
- Emergency contact panel with tap-to-call links: Police `112` / `100` and Ambulance `102` / `108`. Emergency contacts are informational UI only and do not affect route scoring.
- Live departure-time factor connected to the local clock: 07:00–21:00 is the lower-risk window, 21:00–04:00 is higher-risk, and 04:00–07:00 is transitional. No route-distance cutoff is applied during scoring.
- Synthetic police reference points are clearly labelled and must be replaced with verified station data before real deployment.
- Synthetic incidents are not included in the score. If added later, they must retain `is_synthetic: true`, `is_real_crime_data: false`, and a visible “SIMULATED INCIDENT — NOT REAL” label.

## Data separation

- `data/actual_data.json` identifies the supplied road network, streetlight records, and district crime totals.
- `data/synthetic_data.json` identifies prototype-only police points, randomized visualization coordinates, and modeling assumptions.
- The district crime totals are actual supplied records, but their map coordinates are synthetic visualization placements rather than real street-level incident locations.

## Run

Requirements: Python 3.11+.

```bash
python3 backend/server.py
```

Open <http://127.0.0.1:8000/frontend/index.html>.

**Do not double-click `frontend/index.html` in Finder.** That opens it as a
`file://` document, which can be blocked by browser access restrictions and
cannot reach the backend API correctly. Run the backend and open the HTTP URL
above instead.

On macOS, you can double-click `start.command` from the project folder. If
macOS asks for confirmation, choose **Open**. Leave the Terminal window open
while using the prototype.

The launcher checks Python and both data files, starts the backend, and opens
the browser automatically.

If your browser blocks the backend-served page, use a second static server in
another terminal and change the API base URL in `frontend/index.html`:

```bash
python3 -m http.server 8080 --directory frontend
```

Then change the API calls in `frontend/index.html` from `/api/...` to `http://127.0.0.1:8000/api/...`.

The first startup parses the large GraphML file and may take a little while. The demo bounds are derived from the supplied streetlight CSV. Set `MAX_PILOT_NODES` to control laptop memory, or set `GRAPHML_PATH` and `STREETLIGHT_CSV` to use different files.

## API

- `GET /api/health` — loaded node, edge, and streetlight counts.
- `GET /api/map` — GeoJSON road heatmap with lighting status, lighting score, police distance, and risk.
- `GET /api/stations` — configured police reference points; returns `synthetic: true`.
- `POST /api/route` — body:

```json
{"origin":{"lat":13.05497,"lon":77.53473},"destination":{"lat":13.05851,"lon":77.53331}}
```

## Using the location search

Type a pilot location such as `Malleshwaram`, `Peenya`, `Hebbal`, or
`Rajajinagar` into either the origin or destination field, then select the
suggestion shown directly below that field. The search list is deliberately
local and deterministic for the hackathon demo; it does not silently call an
external geocoder or transmit search text to a third party. Locations outside
the supplied pilot network are intentionally not included until a larger road
dataset is configured.

## Risk model

`police_safety = exp(-police_distance_km / 2.0)`

`risk = 0.35 * (1 - lighting_score) + 0.65 * (1 - police_safety)`

The displayed route score is calibrated as `50 + 50 * (1 - average_time_adjusted_risk)`.
This keeps 50 as a neutral baseline: incomplete lighting data lowers confidence
without being presented as proof of severe danger. The underlying risk values
still determine route ordering.

Lighting score is based on supplied streetlight proximity. Missing proximity data produces an infrastructure/data-quality flag and lowers confidence; it does not assert that a road is dark. Police proximity is an emergency-access signal, not a claim about crime.

The route request accepts `departure_time` in `HH:MM` format. When omitted,
the backend uses the current local clock. The selected time changes both route
cost and displayed score; it does not impose a distance limit.

The route request accepts `travellers`, defaulting to `1`, with values from 1
to 20. The group benefit is `min(0.45, 0.15 * log2(travellers))`, so more
travellers improve the calibration with diminishing returns without implying
that a group is guaranteed to be safe.

## Production next steps

1. Replace the synthetic police reference points with verified station coordinates and a publication date.
2. Add real incident data only with provenance, timestamps, aggregation, privacy review, and explicit synthetic/real labels.
3. Use a spatial index and a precomputed edge cache for city-scale deployment; this prototype deliberately caps the loaded pilot node count for a hackathon laptop.
4. Add route snapping, max-detour controls, authenticated incident ingestion, tests, and a deployment configuration.
