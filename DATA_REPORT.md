# Supplied Bengaluru pilot data report

## Streetlights

- File: `data/streetlights.csv`
- Rows: 24,432 data records
- Columns: `pole_id`, `ward`, `latitude`, `longitude`, `page`
- Geometry: point coordinates reconstructed from latitude/longitude
- CRS assumption: WGS84 (`EPSG:4326`), because the file supplies geographic coordinates
- Validation performed: numeric latitude/longitude parsing and geographic bounds check
- Coverage: approximately 12.989–13.092933 latitude and 77.491272–77.540482 longitude

## Roads

- File: `data/roads.graphml`
- Source structure: GraphML road graph with node `x`/`y` coordinates and edge `length`, `highway`, and `geometry` attributes where available
- Reference size: approximately 185,478 node elements and 496,374 edge elements
- Runtime behavior: the prototype derives a pilot envelope from the streetlight coverage and loads the intersecting road network; `MAX_PILOT_NODES` bounds laptop memory for the demo

## Limitations

- The streetlight file does not contain operational status, illumination level, or install date. A nearby point means `verified` for this prototype, not that the lamp works.
- No verified police-station dataset was supplied. Police-distance values currently use clearly labelled synthetic reference points and must not be presented as live emergency coverage.
- No real incident dataset is used in the score. Synthetic incident records, if added later, must be marked as synthetic and displayed as such.
