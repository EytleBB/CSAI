# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CS-Scout: CS2 demo analysis and tactical visualization system for the Mirage map. Two subsystems:

1. **Web server** (`server/`) — Flask VPS server that accepts 5E usernames, auto-fetches demos, and serves CT-side heatmaps + combat stats to a browser UI
2. **Local tools** (`tools/`) — standalone scripts for offline demo analysis, heatmap viewing, zone editing

---

## Web Server System (primary active work)

### Architecture

```
Browser UI (index.html)
    │  POST /api/analyze_by_names  {usernames[], max_demos, key}
    ▼
web_server.py  (Flask, port 5000)
    │  background thread
    ▼
pipeline.run_by_usernames()
    ├── [Download thread]  search_player → get_mirage_demos_by_domain → get_steamid_for_player → download_and_extract
    └── [Main thread]      parse_demo → generate_heatmap → parse_combat_stats → generate_zone_stats
    ▼
output/heatmap_{domain}.png  +  output/tile_{domain}_{rtype}.png  +  output/analysis_summary.json
```

### 5E Platform API (api_client.py)

Two base URLs:
- `https://arena.5eplay.com` — player search, match list with demo URLs
- `https://gate.5eplay.com` — match detail (steamid extraction, old UUID flow)

Key functions:
- `search_player(username)` → `(domain, matched_username)` — domain is URL-safe ID like `0705cupvvglq`
- `get_mirage_demos_by_domain(domain, count=10)` → `[{match_code, demo_url}]`
  - Auto-detects match_type: tries **`?match_type=9` first**, then no-params / `?match_type=1/8`
  - **Critical**: `match_type=9` is ranked mode and always has `demo_url`. No-params returns matches without `demo_url` for many players — trying it first was a bug that caused "无 Mirage demo 可用" for players like emooQAQ, 1015_.
  - Deduplicates across pages via `seen_codes` set
  - Filters for `map == "de_mirage"` with non-empty `demo_url`
- `get_steamid_for_player(match_code, username)` — extracts steamid from match detail by username match
- `download_demo(url, path)` — streams zip to disk

### Pipeline Flow (pipeline.py)

`run_by_usernames` uses a **demo-level pipeline**: the download thread puts each `.dem` file into the queue immediately after extraction, so the main thread starts parsing it while the *next* demo is still downloading.

```
Download thread: [dl dem A1] → [dl dem A2] → [dl dem B1] → ...
Main thread:               ↘ [parse A1] → [parse A2] → [parse B1] → heatmap A → ...
```

Queue `maxsize=10` (demo-level items). Queue item types:
- `{"type": "demo", "i", "username", "domain", "steamid", "demos_found", "dem_file", "dem_idx"}`
- `{"type": "player_done", "i", "username", "domain", "steamid", "demos_found"}`
- `{"type": "player_failed", "i", "username", "reason"}`
- `None` — sentinel

Heatmap and combat stats are computed in the main thread when `player_done` is received.

Per-player pipeline steps (reported via progress_cb):
1. `(0/5)` Search username on 5E arena
2. `(1/5)` Fetch Mirage demo list (auto-detect match_type, paginate)
3. `(2/5)` Resolve steamid from match detail
4. `(3/5)` Download demo N — per-demo as they land
5. `(4/5)` Parse demo N — immediately after each download
6. `(5/5)` Generate heatmap (once all demos parsed)

### Demo Deduplication Index

`download_and_extract(match_id, demo_url, dest_dir)` checks a **global in-memory + on-disk index** before downloading:

- Index file: `server/demos_opponents/.demo_index.json` — `{match_id: [dem_path, ...]}`
- Loaded once on first call, updated after each successful download
- On lookup, invalid (deleted) paths are pruned automatically
- **Why**: 5 grouped opponents often share many of the same match IDs — without dedup, the same 100–200 MB demo would be downloaded 5×

### Demo Disk Cleanup

`cleanup_demos(demo_dir, limit_gb=30, target_gb=10)`:
- Called once at the start of each `run_by_usernames` invocation
- If total `.dem` size > 30 GB: deletes oldest files (by mtime) until total ≤ 10 GB

### Round Number Deduplication

When combining records from multiple demos, round numbers collide (all start from 1). Fix: offset each demo's rounds by `i * 1000`:
```python
for j, dem in enumerate(dem_files):
    records = parse_demo(dem, steamid, zones)
    for rec in records:
        rec["round"] += j * 1000
```

### Heatmap Generation (generate_heatmap)

- **Output**: saves 4 individual tile images (`tile_{domain}_{rtype}.png`) + a combined 2×2 overview image (`heatmap_{domain}.png`). Returns `tile_paths` dict.
- **Atomic write**: saves to `output_path + ".tmp"`, then `os.replace()`. Must pass `format="png"` explicitly to `fig.savefig()`.
- **Gaussian sigma**: `max(3, 7 - n_rounds // 20)` — small min (3 px) for precise positioning
- **Gamma correction**: `grid = np.power(grid, 0.55)` — boosts faint low-density areas
- **Alpha ramp**: `np.linspace(0.02, 0.88, base.N)` — floor of 0.02 keeps all positions visible
- **vmin**: `0.005` — shows more of the heatmap range
- **Per-round normalization**: each round contributes weight 1.0 regardless of tick count (because window end varies with first kill timing)
- **CJK font**: at startup, searches for system CJK fonts. Install `fonts-noto-cjk` on VPS for proper CJK rendering.

### Combat Stats (parse_combat_stats / aggregate_combat_stats)

**K/D** — from demo scoreboard (global, both sides, no CT filter):
- Reads `kills_total` and `deaths_total` tick fields at the last `round_end` tick
- Per-demo K/D computed; `aggregate_combat_stats` averages across demos
- **Why global**: scoreboard K/D is clean and directly comparable; CT-only K/D was inaccurate

**AWP Rate** — CT-side AWP kills / CT-side total kills:
- Filters `player_death` events to CT rounds only (using `fe_tick`/`end_tick` from `classify_rounds`)
- AWP kills = deaths where `attacker_steamid == target` and `weapon in SNIPER_EVENT_NAMES`
- `SNIPER_EVENT_NAMES = {"awp", "ssg08", "g3sg1", "scar20"}` — plain event weapon names
- Aggregated as: `sum(awp_kills) / sum(ct_kills)` across all demos

**ADR removed** — `dmg_health` in CS2 is uncapped raw bullet damage (AWP headshot = 446+), making accurate ADR calculation unreliable. Field removed from pipeline and UI.

### State & API Endpoints

`web_server.py` global `state` dict (protected by `state_lock`):
```python
state = {
    "status":        "idle",   # idle / running / done / error
    "message":       "",
    "progress":      [],       # [{id, step, msg}, ...]
    "results":       [],       # successful player results
    "failed":        [],       # [{username, reason}, ...]
    "total_players": 0,
    "max_demos":     10,
}
```

Endpoints:
- `POST /api/analyze_by_names` — main entry: `{usernames[], max_demos, key}`
- `GET  /api/status` — returns full state dict (polled every 2s by frontend)
- `GET  /api/results` — loads `analysis_summary.json` from disk
- `GET  /output/<file>` — serves heatmap PNGs
- `GET  /` — serves `index.html`

### analysis_summary.json Format (current)

```json
{
  "max_demos": 10,
  "failed": [{"username": "X", "reason": "..."}],
  "results": [
    {
      "username": "...", "domain": "...",
      "heatmap": "heatmap_{domain}.png",
      "tiles": {
        "Full Buy": "tile_{domain}_fullbuy.png",
        "Force Buy": "tile_{domain}_forcebuy.png",
        "Eco": "tile_{domain}_eco.png",
        "Pistol": "tile_{domain}_pistol.png"
      },
      "zone_stats": {...},
      "combat_stats": {"kd": 1.23, "awp_rate": 45.0},
      "demos_found": 5, "demo_count": 5,
      "record_count": 430, "round_count": 47
    }
  ]
}
```

`/api/results` normalizes heatmap and tile paths by prepending `/output/` if not already present. Frontend does **not** add the prefix.

### Frontend (index.html)

- **Layout**: sticky 50px header + two-column body (220px left sidebar + 1fr right panel). Body height = `100vh - 50px`, no page scroll.
- **Left panel**: 5 username inputs, demo depth slider, Execute Scan button, status box, data coverage (adequacy bars), failed targets section.
- **Failed section**: lives at the **bottom of the left panel** (not in main content area), shown in red when any player scan fails.
- **Right panel**: player tabs + card per player. Card = card-header + two-column card-body (heatmap grid left, stats+zones right).
- **Heatmap grid**: 2×2 tile grid, `height: calc(100vh - 210px)` so all 4 tiles are visible without scrolling. Left-click a tile to expand it (fills full 2×2 area with `tileExpand` CSS animation, `cubic-bezier` easing). Right-click to collapse.
- **Combat stats**: K/D (global) and AWP率 in a 2-column stat-grid.
- **Zone stats**: per round-type (Full Buy / Force Buy / Eco / Pistol) zone distribution bars.
- **Page load**: checks `/api/status` first → resumes polling if `running`, renders state if `done`, falls back to `/api/results` if `idle`/`error`.
- **Adequacy bar**: per-player color-coded coverage % tags.
- **List input**: `[name1, name2, name3]` format in any box is parsed as a comma-separated list.

### Known Data Limitations

- Players with no Mirage ranked games: `get_mirage_demos_by_domain` returns empty → reported as failed.
- `match_type=9` is ranked mode and always includes `demo_url`. No-params / other match_types often return matches with empty `demo_url` — so `match_type=9` must be tried first.
- `get_steamid_for_player` matches by username string — fails if username changed since the match.
- K/D is global (both sides). CT-only K/D not implemented (CT-side kill detection from events is fragile).

### VPS Deployment

Server runs on Ubuntu VPS at `/home/ubuntu/server/`. Start command:
```bash
cd /home/ubuntu/server
source venv/bin/activate
python web_server.py
```

Python deps (install in venv):
```bash
pip install flask numpy pandas matplotlib scipy shapely demoparser2 requests
```

Access at `http://<VPS公网IP>:5000` — ensure port 5000 is open in security group.

### Debug / Diagnostic Tools (local)

`D:/CSAI/debug_api_diagnose.py` — checks why players show "无 Mirage demo 可用". Queries all match_types for each username and reports map distribution + demo_url availability. No downloads. Run with proxy active.

---

## Local Analysis Tools (legacy/offline)

Located in `tools/` and `D:/CSAI/` root.

### Running Scripts

```bash
python algo_batch_processor.py   # Text report: CT positioning per player/round-type
python tool_heatmap.py           # Interactive heatmap viewer (matplotlib UI)
python tool_visualize_path.py    # Path overlay on radar for a single player/round
python algo_position_map.py      # Scatter plot of raw position data
python map_zone_editor.py        # GUI: draw/edit zone polygons on radar image
python tool_map_calibrator.py    # GUI: calibrate game→pixel coordinate transform
python zone_priority_manager.py  # GUI: assign zone priority weights
python batch_downloader.py       # Scrape Mirage demo download links from 5E platform
python match_crawler.py          # JS-injection crawler for individual match pages
```

### Tracked Players & Round Classification

CT_PLAYERS dict (hardcoded in `algo_batch_processor.py` and `tool_heatmap.py`) maps Steam ID → display name.

Round types determined at `round_freeze_end` tick by CT team average `current_equip_value`:
- **Pistol** — first round of each CT segment
- **Full Buy** ≥ 3800
- **Force Buy** ≥ 1500
- **Eco** < 1500

### Analysis Window

`freeze_end` to `first_kill_in_round + 3s` (sampled every 64 ticks). Captures initial positioning before engagements.

### Coordinate System

`map_config.json` defines the transform (`pos_x: -3230`, `pos_y: 1713`, `scale: 5.0`):
```python
pixel_x = (game_x - pos_x) / scale
pixel_y = (pos_y - game_y) / scale   # Y axis is inverted
```

### Zone System

`mirage_zones.json` — named polygon zones in **game coordinates** (not pixel).
`zone_weights.json` — priority weights: `1`=default, `2`=key control, `3`=high-risk aggression.
Containment check: `shapely.geometry.Point.within(Polygon)` iterates all zones; first match wins.

### demoparser2 API Pattern

```python
parser = DemoParser(path)
evts = dict(parser.parse_events(["round_freeze_end", "round_end"], other=["tick"]))
df = parser.parse_ticks(["X", "Y", "steamid", "team_name"], ticks=[tick1, tick2, ...])
```
Always cast result to `pd.DataFrame` and cast `steamid` to `str`.

**Known field notes**:
- `dmg_health` — uncapped raw bullet damage (AWP headshot = 446+). Cap at 100 if computing effective damage.
- `kills_total`, `deaths_total` — scoreboard running totals, available as tick fields. Reliable for end-of-match K/D.
- `weapon` in `player_death`/`player_hurt` events — plain name (e.g. `"awp"`, `"ak47"`), not prefixed.
- `active_weapon_name` — NOT a valid demoparser2 tick field (silently returns nothing). Use event `weapon` field instead.

## Config & Data Files

| File | Purpose |
|------|---------|
| `server/config.py` | VPS config: HOST, PORT, SECRET_KEY, paths |
| `server/data/map_config.json` | Coordinate transform parameters |
| `server/data/mirage_zones.json` | Zone polygon definitions (game coords) |
| `server/data/zone_weights.json` | Tactical priority per zone |
| `server/data/de_mirage_radar.png` | Radar image used as visualization background |
| `server/demos_opponents/` | Downloaded .dem files + `.demo_index.json` |
| `server/output/` | Generated heatmaps (tile + combined) + analysis_summary.json |

## Debug & Inspection Tools

```bash
python debug_round_inspector.py   # Inspect round structure and events
python debug_event_list.py        # List all event types in a demo
python debug_zone_verifier.py     # Validate zones against real trajectories
python demo_inspector.py          # General demo structure diagnostics
python tool_check_players.py      # Verify player Steam IDs in a demo
```
