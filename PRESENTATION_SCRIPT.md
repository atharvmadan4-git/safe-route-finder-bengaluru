# Safe Route Finder — presentation script

## Opening: the problem

“Good morning. My project is Safe Route Finder, a safety-aware walking route
prototype for Bengaluru.

Most map applications optimise for the shortest or fastest route. At night,
that is not always the route a person wants. A route can be shorter but pass
through segments where lighting has not been verified or where emergency
access is farther away.

My goal was not to claim that an algorithm can guarantee safety. The goal was
to make the available evidence visible and compare route trade-offs
transparently.”

## What the user sees

“The user searches for a named origin and destination in the Bengaluru pilot
area. They choose a departure time and the number of travellers.

The application returns three route options:

- Fastest
- Balanced
- Safest

For each route, the interface shows distance, estimated walking time, safety
score, percentage of route with verified lighting, police-proximity safety,
time factor, and any data-quality flags.

The map shows green road segments where the supplied streetlight data supports
a nearby light reference, and red segments where lighting is unverified.”

## Live demo sequence

“I will demonstrate a route from Peenya pilot edge to Hebbal pilot edge.

First, I select one traveller and a daytime departure such as 10:00. The
system calculates the three route options.

Next, I change the departure time to 21:20. The score changes, but only
gradually. Early evening is not treated the same as the middle of the night.

Then I try 02:00. The deeper-night time factor lowers the displayed score
more strongly.

Finally, I change the group size from one to four travellers. The score
increases because the model applies a capped group benefit with diminishing
returns. This is a calibration assumption, not a guarantee that a group is
safe.”

## How the code is organised

“The prototype has a small backend and frontend.

`backend/server.py` is the complete local backend. It:

1. Loads the streetlight CSV.
2. Reads the GraphML road network.
3. Restricts loading to the streetlight coverage envelope so the large input
   can run on a normal laptop.
4. Builds a small grid index for streetlight proximity.
5. Scores every road edge.
6. Runs weighted shortest-path routing.
7. Serves JSON APIs for health, map data, stations, and route comparison.

`frontend/index.html` is a dependency-light Leaflet interface. It:

1. Displays the road layers.
2. Provides named origin and destination search.
3. Sends route requests to the backend.
4. Draws the returned route geometries.
5. Displays route explanations and emergency contact buttons.

The application is intentionally easy to run: `start.command` checks that the
data files exist, starts the backend, and opens the browser.”

## Data used

“The real pilot inputs supplied for this project are:

- A GraphML road network containing nodes, coordinates, directed edges, road
  lengths, and road attributes.
- A CSV with 24,432 streetlight records containing pole ID, ward, latitude,
  longitude, and source page.

The CSV does not say whether a light is working. Therefore, the interface
uses the word ‘verified’ carefully: it means that a supplied streetlight
record was found near the road segment, not that the lamp is currently
illuminated.

Police points are synthetic reference points in this offline prototype. They
are clearly labelled and must be replaced with verified station data before
real deployment.”

## Lighting calculation

“For each road edge, the backend finds the midpoint. It checks nearby grid
cells and measures the geographic distance from that midpoint to the supplied
streetlight coordinates.

The current rule is:

```text
verified lighting = at least one supplied streetlight within 35 metres
unverified lighting = no supplied streetlight within 35 metres
```

The lighting score is:

```text
lighting_score =
  min(1, nearby_light_count / max(edge_length_metres / 100, 1))
```

This rewards more nearby lights on longer segments. The prototype uses
‘unverified’ rather than ‘dark’ because missing data is not proof of darkness.”

## Police-proximity calculation

“For each edge, the backend calculates distance to the nearest configured
police reference point.

The positive police-proximity factor is:

```text
police_safety = exp(-distance_km / 2.0)
```

This means the factor is highest near a station and decays smoothly with
distance. It is an emergency-access signal, not a prediction that crime
occurs farther away.

The route also shows a warning when a segment is more than 1.5 kilometres
from the nearest reference point. That warning is about mapped assistance
distance, not confirmed danger.”

## Time and traveller calculations

“The departure time is connected to the local clock by default, but the user
can override it.

The current time calibration is:

- 07:00 to 21:00: factor 1.00
- 21:00 to 23:00: factor 0.92
- 23:00 to 04:00: factor 0.78
- 04:00 to 07:00: factor 0.88

These are deliberately gradual calibration values. A 21:20 trip in a busy
urban area should not be treated like a 02:00 trip.

For travellers, the benefit is:

```text
group_benefit = min(0.45, 0.15 * log2(number_of_travellers))
```

One traveller gets no group benefit. Additional travellers help, but the
benefit saturates and cannot make the score perfect.”

## Combined route model

“The edge risk combines lighting and police proximity:

```text
edge_risk =
  0.35 * (1 - lighting_score)
  + 0.65 * (1 - police_safety)
```

Police proximity has the larger weight in this prototype because quick access
to assistance is important for the intended use case.

For routing, the edge cost is:

```text
route_cost = edge_length * (1 + route_mode_weight * time_adjusted_risk)
```

The fastest route uses a route-mode weight of zero. Balanced and safest use
larger weights, so they may choose a path with different safety evidence.

The displayed score is calibrated around a neutral baseline:

```text
displayed_score =
  50 + 50 * (1 - average_time_adjusted_risk)
```

This prevents incomplete lighting data from being displayed as if it were
confirmed severe danger. The underlying risk still determines route ordering.”

## Responsible-use explanation

“There are important limitations.

The application does not predict crime. It does not know whether a streetlight
works, and its police points are synthetic. The streetlight data is also
measured using a prototype midpoint rule, so a production system should split
long edges and use full line geometry.

Future improvements would include verified police locations, streetlight
maintenance status, pedestrian activity by hour, sidewalks and crossings,
transit access, and carefully anonymised incident data.

The most important design decision is that the product exposes uncertainty
instead of hiding it.”

## Closing

“Safe Route Finder demonstrates how real infrastructure data can support a
more transparent route comparison for night travel.

It is not saying, ‘this route is safe.’ It is saying, ‘based on the available
data, this route has stronger or weaker evidence, and here is why.’

That makes the recommendation more explainable, more honest, and easier to
improve as better Bengaluru data becomes available.”

