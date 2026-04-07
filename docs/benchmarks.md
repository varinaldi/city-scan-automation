# Benchmark Cities

**benchmark_mode** — controls which sources to use:
- `sibling` — only sibling scans, no Oxford
- `oxford` — only Oxford auto-detect, no siblings
- `auto` (default/null) — both sibling + Oxford auto-detect

**bm_cities_manual** — explicit list of cities. These get resolved based on what's available:
- If it's a sibling → use WorldPop from sibling scan
- If it's in Oxford → use Oxford data
- If neither → use benchmark_backup

**benchmark_backup** — fallback for manual cities not found as sibling or Oxford:
- `citypopulation` — citypopulation.de + OSM boundary
- `worldpop_ucdb` — WorldPop + UCDB boundary
- null — skip

**nearby_countries** — only relevant when mode includes Oxford (`oxford` or `auto`). Filters which countries to look for Oxford cities in.
