# Safe Route Finder — Hackathon submission

## One-line pitch

Safe Route Finder helps people compare walking routes at night using real
Bengaluru streetlight reference data, police-proximity context, departure time,
and group size—while clearly separating verified data from uncertainty.

## Problem

The shortest walking route is not always the route people feel safest using
after dark. Existing route tools optimise primarily for distance and time, and
often hide how incomplete their safety data is.

## Solution

The prototype compares three route strategies:

- **Fastest** — shortest travel cost.
- **Balanced** — trades a small amount of time for lower modelled risk.
- **Safest** — gives the safety model the strongest influence.

Each route shows distance, walking time, safety score, streetlight coverage,
police-proximity safety, traveller count, time factor, and explicit flags.

## What is real in this demo

- Supplied Bengaluru GraphML road network.
- Supplied CSV containing 24,432 streetlight pole locations.
- Streetlight coverage evaluated against road-segment midpoints.
- Interactive map rendered with Leaflet.

Police points are synthetic reference points for demonstration and are labelled
as such in the interface and documentation. They must be replaced with verified
station data before deployment.

## Responsible design

- An unverified streetlight segment does **not** mean the road is dark.
- Safety flags describe possible concerns and data limitations; they are not
  confirmed crime incidents.
- Group size creates a capped, diminishing calibration benefit; it does not
  guarantee safety.
- Synthetic incidents, if added later, must remain visibly labelled as
  simulated and must never be presented as police reports.

## Demo flow

1. Start the app with `start.command`.
2. Search for `Peenya pilot edge` as the origin.
3. Search for `Hebbal pilot edge` as the destination.
4. Try departure times `10:00`, `21:20`, and `02:00`.
5. Compare one traveller with four travellers.
6. Explain why a route can be longer but score better.
7. Show the green verified-lighting roads and red unverified roads on the map.
8. Demonstrate the tap-to-call emergency contacts without claiming that the
   prototype is an emergency dispatch service.

## Judging criteria this prototype demonstrates

| Criterion | Evidence |
| --- | --- |
| Real-world relevance | Bengaluru road and streetlight data |
| Technical implementation | GraphML parsing, spatial grid lookup, weighted routing |
| User experience | Named place search, interactive map, route cards |
| Explainability | Factor percentages, flags, assumptions, plain-English output |
| Responsible innovation | Provenance labels, synthetic-data disclosure, no crime claims |
| Extensibility | Replaceable data files and environment-variable configuration |

## Future work

Replace synthetic police points with verified locations, add streetlight
operational status, split long road edges into smaller segments, add
pedestrian-activity and sidewalk data, and validate the model with community
research and safety experts.

