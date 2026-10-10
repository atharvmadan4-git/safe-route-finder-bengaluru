# Data sources and provenance

## Road network

- File: `data/roads.graphml`
- Format: GraphML
- Used for: walkable nodes, directed edges, lengths, and route geometry
- Provenance: supplied as part of the project inputs

## Streetlights

- File: `data/streetlights.csv`
- Format: CSV
- Columns: `pole_id`, `ward`, `latitude`, `longitude`, `page`
- Used for: proximity-based lighting reference
- Provenance: supplied as part of the project inputs
- Important limitation: the file does not establish whether a lamp is
  functioning, illuminated, or recently inspected

## Police reference points

The current prototype uses three synthetic reference points so the
police-proximity factor can be demonstrated offline. They are not verified
police-station coordinates and must not be used for real emergency navigation.

