"""
CS2 CT heatmap viewer
- Top button row: select player
- Bottom button row: select round type
- Single map view, switches on click
- Data loaded once from all demos, then filtered in-memory
"""
import os
import json
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.widgets import Button
from scipy.ndimage import gaussian_filter
from demoparser2 import DemoParser
from shapely.geometry import Point, Polygon

DEMO_FOLDER = r"demos_analysis"
MAP_IMG     = "de_mirage_radar.png"
CONFIG_FILE = "map_config.json"
ZONES_FILE  = "mirage_zones.json"

CT_PLAYERS = {
    "76561199203609695": "Fei667",
    "76561199164018682": "ShenLi",
    "76561199073048009": "EggingGod",
    "76561199523741371": "Yonghu",
    "76561199781942516": "cs_zhizhe",
}

WINDOW_START_S = 8
WINDOW_END_S   = 22
TICK_RATE      = 64

EQ_FULL_BUY  = 3800
EQ_FORCE_BUY = 1500

RTYPE_ORDER = ["Full Buy", "Force Buy", "Eco", "Pistol"]
RTYPE_CMAP  = {
    "Full Buy":  "Reds",
    "Force Buy": "Oranges",
    "Eco":       "YlOrBr",
    "Pistol":    "cool",
}

# Per-player color when multiple players are selected simultaneously
PLAYER_CMAP = {
    "Fei667":    "Reds",
    "ShenLi":    "Blues",
    "EggingGod": "Greens",
    "Yonghu":    "Purples",
    "cs_zhizhe": "Oranges",
}

COL_ACTIVE   = "#4a90d9"
COL_INACTIVE = "#2a2a3e"
COL_TEXT     = "white"


# ── data loading ──────────────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"pos_x": -3230, "pos_y": 1713, "scale": 5.0}


def load_zones():
    if not os.path.exists(ZONES_FILE):
        return {}
    with open(ZONES_FILE, encoding="utf-8") as f:
        return json.load(f)


def game_to_pixel(cfg, gx, gy):
    return (gx - cfg["pos_x"]) / cfg["scale"], (cfg["pos_y"] - gy) / cfg["scale"]


def get_round_table(parser):
    raw = parser.parse_events(
        ["round_freeze_end", "round_announce_match_start", "round_end"],
        other=["tick"]
    )
    evts = dict(raw)
    match_tick = int(evts["round_announce_match_start"]["tick"].iloc[0])
    fe_all = evts["round_freeze_end"]["tick"].sort_values().reset_index(drop=True)
    re_all = evts["round_end"]["tick"].sort_values().reset_index(drop=True)
    real_fe = fe_all[fe_all >= match_tick].reset_index(drop=True)

    rounds = []
    for i, fe_tick in enumerate(real_fe):
        later_ends = re_all[re_all > fe_tick]
        end_tick = int(later_ends.iloc[0]) if not later_ends.empty else fe_tick + 115 * TICK_RATE
        rounds.append({"official_num": i + 1, "fe_tick": int(fe_tick), "end_tick": end_tick})
    return rounds


def classify_rounds(parser, rounds, target_sids):
    result = []
    prev_was_ct = False
    pistol_num = None

    for r in rounds:
        df = parser.parse_ticks(
            ["steamid", "team_name", "current_equip_value"], ticks=[r["fe_tick"]]
        )
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        df["steamid"] = df["steamid"].astype(str)

        targets = df[df["steamid"].isin(target_sids)]
        if targets.empty:
            prev_was_ct = False
            result.append({**r, "is_ct": False, "round_type": None})
            continue

        is_ct = targets["team_name"].iloc[0] == "CT"
        if is_ct:
            if not prev_was_ct:
                pistol_num = r["official_num"]
            if r["official_num"] == pistol_num:
                rtype = "Pistol"
            else:
                avg_eq = df[df["team_name"] == "CT"]["current_equip_value"].mean()
                rtype = ("Full Buy" if avg_eq >= EQ_FULL_BUY
                         else "Force Buy" if avg_eq >= EQ_FORCE_BUY
                         else "Eco")
        else:
            rtype = None

        prev_was_ct = is_ct
        result.append({**r, "is_ct": is_ct, "round_type": rtype})

    return result


def collect_all(demo_files):
    """Load all demos, return combined DataFrame with columns:
    player, steamid, round, round_type, X, Y
    """
    target_sids = set(CT_PLAYERS.keys())
    all_records = []

    for path in demo_files:
        print(f"Parsing: {os.path.basename(path)}")
        parser = DemoParser(path)
        rounds = get_round_table(parser)
        if not rounds:
            continue

        classified = classify_rounds(parser, rounds, target_sids)
        ct_rounds = [r for r in classified if r["is_ct"]]
        if not ct_rounds:
            continue

        type_map = {r["official_num"]: r["round_type"] for r in ct_rounds}
        sample_ticks = []
        tick_to_round = {}
        for r in ct_rounds:
            lo = r["fe_tick"] + WINDOW_START_S * TICK_RATE
            hi = min(r["fe_tick"] + WINDOW_END_S * TICK_RATE, r["end_tick"])
            if lo >= hi:
                continue
            for t in range(lo, hi, TICK_RATE):
                sample_ticks.append(t)
                tick_to_round[t] = r["official_num"]

        if not sample_ticks:
            continue

        df_all = parser.parse_ticks(["X", "Y", "steamid", "team_name"], ticks=sample_ticks)
        if not isinstance(df_all, pd.DataFrame):
            df_all = pd.DataFrame(df_all)
        if df_all.empty:
            continue

        df_all["steamid"] = df_all["steamid"].astype(str)
        df_ct = df_all[
            (df_all["steamid"].isin(target_sids)) & (df_all["team_name"] == "CT")
        ].copy()

        df_ct["official_round"] = df_ct["tick"].map(tick_to_round)
        df_ct = df_ct.dropna(subset=["official_round"])
        df_ct["official_round"] = df_ct["official_round"].astype(int)

        for _, row in df_ct.iterrows():
            rnum = row["official_round"]
            sid = row["steamid"]
            all_records.append({
                "player":     CT_PLAYERS[sid],
                "steamid":    sid,
                "round":      rnum,
                "round_type": type_map[rnum],
                "X":          row["X"],
                "Y":          row["Y"],
            })

        print(f"  -> {len(df_ct)} records from {len(ct_rounds)} CT rounds")

    return pd.DataFrame(all_records) if all_records else pd.DataFrame()


# ── rendering ─────────────────────────────────────────────────────────────────

def draw_zones(ax, cfg, zones):
    for z_name, coords in zones.items():
        pixels = [game_to_pixel(cfg, p[0], p[1]) for p in coords]
        poly = MplPolygon(pixels, closed=True, edgecolor="white", facecolor="none",
                          linewidth=0.5, alpha=0.35)
        ax.add_patch(poly)
        cx = sum(p[0] for p in pixels) / len(pixels)
        cy = sum(p[1] for p in pixels) / len(pixels)
        ax.text(cx, cy, z_name, color="white", fontsize=5,
                ha="center", va="center", alpha=0.45)


def render(ax, cfg, zones, img, layers):
    """layers: list of (pts, cmap_name) — each entry is one heatmap layer to overlay."""
    ax.clear()
    ax.imshow(img)
    draw_zones(ax, cfg, zones)
    ax.axis("off")

    h, w = img.shape[:2]
    for pts, cmap_name in layers:
        if not pts:
            continue
        grid = np.zeros((h, w))
        for gx, gy in pts:
            px, py = game_to_pixel(cfg, gx, gy)
            xi, yi = int(round(px)), int(round(py))
            if 0 <= xi < w and 0 <= yi < h:
                grid[yi, xi] += 1
        if grid.max() == 0:
            continue
        # Larger sigma so sparse data (few rounds) still shows a visible spread.
        # Scale sigma slightly with sample count so dense data stays sharp.
        sigma = max(18, 30 - len(pts) // 10)
        grid = gaussian_filter(grid, sigma=sigma)
        grid /= grid.max()
        base = plt.get_cmap(cmap_name)
        rgba = base(np.arange(base.N))
        rgba[:, -1] = np.linspace(0, 0.82, base.N)
        ax.imshow(grid, cmap=mcolors.ListedColormap(rgba), vmin=0.02, vmax=1.0)


# ── interactive UI ────────────────────────────────────────────────────────────

def show_viewer(df, cfg, zones, img):
    players   = sorted(df["player"].unique())
    all_types = RTYPE_ORDER  # fixed order, grey out unavailable

    state = {
        "players": {players[0]},   # set — supports multiple simultaneous selections
        "rtype":   None,
    }

    # ── figure layout ──
    fig = plt.figure(figsize=(10, 12), facecolor="#1a1a2e")
    ax_map = fig.add_axes([0.0, 0.13, 1.0, 0.87])
    ax_map.set_facecolor("#1a1a2e")

    title_obj = fig.text(0.5, 0.995, "", ha="center", va="top",
                         color="white", fontsize=11, fontweight="bold")

    # ── player buttons (top row of buttons) ──
    n_p   = len(players)
    p_w   = min(0.17, 0.9 / n_p)
    p_gap = 0.01
    p_total = n_p * p_w + (n_p - 1) * p_gap
    p_x0  = (1.0 - p_total) / 2

    player_btns = {}
    for i, p in enumerate(players):
        bx  = p_x0 + i * (p_w + p_gap)
        bax = fig.add_axes([bx, 0.07, p_w, 0.045])
        btn = Button(bax, p, color=COL_INACTIVE, hovercolor="#5aabff")
        btn.label.set_color(COL_TEXT)
        btn.label.set_fontsize(8)
        player_btns[p] = (bax, btn)

    # ── round-type buttons (bottom row) ──
    n_t   = len(all_types)
    t_w   = min(0.17, 0.9 / n_t)
    t_gap = 0.01
    t_total = n_t * t_w + (n_t - 1) * t_gap
    t_x0  = (1.0 - t_total) / 2

    type_btns = {}
    for i, rt in enumerate(all_types):
        bx  = t_x0 + i * (t_w + t_gap)
        bax = fig.add_axes([bx, 0.015, t_w, 0.045])
        btn = Button(bax, rt, color=COL_INACTIVE, hovercolor="#5aabff")
        btn.label.set_color(COL_TEXT)
        btn.label.set_fontsize(8)
        type_btns[rt] = (bax, btn)

    def refresh():
        selected = state["players"]
        rtype    = state["rtype"]
        multi    = len(selected) > 1

        # Available types = union across all selected players
        available_types = set()
        for p in selected:
            available_types |= set(df[df["player"] == p]["round_type"].unique())

        # Update player button highlights
        # Must update btn.color (Button's internal "resting" color) so hover-leave
        # doesn't reset it back to the old value.
        for p, (bax, btn) in player_btns.items():
            c = COL_ACTIVE if p in selected else COL_INACTIVE
            btn.color = c
            bax.set_facecolor(c)

        # Update type button highlights + availability
        for rt, (bax, btn) in type_btns.items():
            if rt not in available_types:
                c = "#111118"
                btn.label.set_alpha(0.3)
            elif rt == rtype:
                c = COL_ACTIVE
                btn.label.set_alpha(1.0)
            else:
                c = COL_INACTIVE
                btn.label.set_alpha(1.0)
            btn.color = c
            bax.set_facecolor(c)

        # Build heatmap layers — one per selected player
        layers = []
        stats_parts = []
        for p in sorted(selected):
            p_df = df[df["player"] == p]
            if rtype and rtype in p_df["round_type"].values:
                sub = p_df[p_df["round_type"] == rtype]
                pts = list(zip(sub["X"], sub["Y"]))
                n_rounds  = sub["round"].nunique()
                n_samples = len(pts)
                stats_parts.append(f"{p}({n_rounds}r/{n_samples}s)")
            else:
                pts = []
            # In multi-player mode use per-player color; single player uses round-type color
            cmap = PLAYER_CMAP.get(p, "Reds") if multi else (RTYPE_CMAP.get(rtype, "Reds") if rtype else "Reds")
            layers.append((pts, cmap))

        if rtype:
            title_obj.set_text(f"[{rtype}]  " + "  |  ".join(stats_parts) if stats_parts
                               else f"[{rtype}]  — no data for selection")
        else:
            title_obj.set_text("  +  ".join(sorted(selected)) + "  — select a round type")

        render(ax_map, cfg, zones, img, layers)
        fig.canvas.draw_idle()

    def on_player(p):
        # Toggle: add if not selected, remove if already selected (keep at least one)
        if p in state["players"]:
            if len(state["players"]) > 1:
                state["players"].discard(p)
        else:
            state["players"].add(p)

        # Ensure rtype is still valid for the new selection
        available = set()
        for pl in state["players"]:
            available |= set(df[df["player"] == pl]["round_type"].unique())
        if state["rtype"] not in available:
            state["rtype"] = next((rt for rt in RTYPE_ORDER if rt in available), None)
        refresh()

    def on_type(rt):
        state["rtype"] = rt
        refresh()

    for p, (_, btn) in player_btns.items():
        btn.on_clicked(lambda _, _p=p: on_player(_p))
    for rt, (_, btn) in type_btns.items():
        btn.on_clicked(lambda _, _rt=rt: on_type(_rt))

    # Initial render
    on_player(players[0])
    plt.show()


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    cfg   = load_config()
    zones = load_zones()

    if not os.path.exists(MAP_IMG):
        print(f"Map image not found: {MAP_IMG}")
        return

    img = plt.imread(MAP_IMG)

    demo_files = glob.glob(os.path.join(DEMO_FOLDER, "*.dem"))
    if not demo_files:
        print("No .dem files in demos_analysis/")
        return

    df = collect_all(demo_files)
    if df.empty:
        print("No data collected")
        return

    print(f"\nTotal records: {len(df)}")
    print(f"Players: {sorted(df['player'].unique())}")
    show_viewer(df, cfg, zones, img)


if __name__ == "__main__":
    main()
