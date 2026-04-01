"""
CS2 CT-side positioning analyzer
- Analyzes all 5 CT players per demo
- Window: freeze_end+8s to freeze_end+22s
- Round type: determined by CT team avg equipment value at freeze_end
- Supports merging multiple demos for the same player
"""
import os
import json
import glob
import pandas as pd
from demoparser2 import DemoParser
from shapely.geometry import Point, Polygon

DEMO_FOLDER  = r"demos_analysis"
ZONES_FILE   = "mirage_zones.json"
WEIGHTS_FILE = "zone_weights.json"

# CT team for this match — populated dynamically per demo
# Key: steamid (str), Value: display name
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

# Equipment value thresholds for CT team average at freeze_end
EQ_FULL_BUY  = 3800   # >= Full Buy
EQ_FORCE_BUY = 1500   # >= Force Buy
# < 1500 = Eco


def load_zones():
    if not os.path.exists(ZONES_FILE):
        return []
    with open(ZONES_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    return [{"name": n, "poly": Polygon(coords)} for n, coords in raw.items()]


def load_weights():
    if not os.path.exists(WEIGHTS_FILE):
        return {}
    with open(WEIGHTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_zone(zones, x, y):
    p = Point(x, y)
    for z in zones:
        if z["poly"].contains(p):
            return z["name"]
    return "Unclassified"


def get_round_table(parser):
    """Return list of official rounds (warmup excluded), each with fe_tick, end_tick."""
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
        official_num = i + 1
        later_ends = re_all[re_all > fe_tick]
        end_tick = int(later_ends.iloc[0]) if not later_ends.empty else fe_tick + 115 * TICK_RATE
        rounds.append({
            "official_num": official_num,
            "fe_tick": int(fe_tick),
            "end_tick": end_tick,
        })
    return rounds


def classify_rounds(parser, rounds, target_sids):
    """
    For each round, determine:
    - whether target players are CT
    - round type via CT team avg equipment value at freeze_end
    - pistol round = first round of each continuous CT segment

    Returns: list of round dicts with added keys: is_ct, round_type
    """
    result = []
    prev_was_ct = False
    ct_segment_pistol = None

    for r in rounds:
        fe_tick = r["fe_tick"]
        df = parser.parse_ticks(
            ["steamid", "team_name", "current_equip_value"],
            ticks=[fe_tick]
        )
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        df["steamid"] = df["steamid"].astype(str)

        targets = df[df["steamid"].isin(target_sids)]
        if targets.empty:
            prev_was_ct = False
            result.append({**r, "is_ct": False, "round_type": None})
            continue

        is_ct = (targets["team_name"].iloc[0] == "CT")

        if is_ct:
            # Detect start of CT segment -> pistol round
            if not prev_was_ct:
                ct_segment_pistol = r["official_num"]

            if r["official_num"] == ct_segment_pistol:
                round_type = "Pistol"
            else:
                ct_rows = df[df["team_name"] == "CT"]
                avg_eq = ct_rows["current_equip_value"].mean() if not ct_rows.empty else 0
                if avg_eq >= EQ_FULL_BUY:
                    round_type = "Full Buy"
                elif avg_eq >= EQ_FORCE_BUY:
                    round_type = "Force Buy"
                else:
                    round_type = "Eco"
        else:
            round_type = None

        prev_was_ct = is_ct
        result.append({**r, "is_ct": is_ct, "round_type": round_type})

    return result


def parse_demo(path, zones):
    """
    Parse one demo file.
    Returns list of records: {player, steamid, round, round_type, zone, X, Y}
    """
    parser = DemoParser(path)
    rounds = get_round_table(parser)
    if not rounds:
        return []

    target_sids = set(CT_PLAYERS.keys())
    classified = classify_rounds(parser, rounds, target_sids)
    ct_rounds = [r for r in classified if r["is_ct"]]

    if not ct_rounds:
        return []

    ct_nums = [r["official_num"] for r in ct_rounds]
    type_map = {r["official_num"]: r["round_type"] for r in ct_rounds}
    print(f"  CT rounds: {ct_nums}")
    print(f"  Types: { {n: type_map[n] for n in ct_nums} }")

    # Build sample ticks: fe+8s to fe+22s (capped at round_end)
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
        return []

    cols = ["X", "Y", "steamid", "team_name"]
    df_all = parser.parse_ticks(cols, ticks=sample_ticks)
    if not isinstance(df_all, pd.DataFrame):
        df_all = pd.DataFrame(df_all)
    if df_all.empty:
        return []

    df_all["steamid"] = df_all["steamid"].astype(str)
    df_ct = df_all[
        (df_all["steamid"].isin(target_sids)) & (df_all["team_name"] == "CT")
    ].copy()

    df_ct["official_round"] = df_ct["tick"].map(tick_to_round)
    df_ct = df_ct.dropna(subset=["official_round"])
    df_ct["official_round"] = df_ct["official_round"].astype(int)

    records = []
    for _, row in df_ct.iterrows():
        rnum = row["official_round"]
        sid = row["steamid"]
        zone = get_zone(zones, row["X"], row["Y"])
        records.append({
            "player":     CT_PLAYERS[sid],
            "steamid":    sid,
            "round":      rnum,
            "round_type": type_map[rnum],
            "zone":       zone,
            "X":          row["X"],
            "Y":          row["Y"],
        })

    return records


def print_report(df, weights):
    ORDER = ["Pistol", "Full Buy", "Force Buy", "Eco"]
    ICON  = {1: "[D]", 2: "[K]", 3: "[A]"}

    sep = "=" * 65
    print(sep)
    print("  CS2 CT positioning report (Mirage)")
    print(sep)

    for player in sorted(df["player"].unique()):
        p_df = df[df["player"] == player]
        print(f"\n[{player}]  samples: {len(p_df)}, rounds: {p_df['round'].nunique()}")

        for rtype in ORDER:
            r_df = p_df[p_df["round_type"] == rtype]
            if r_df.empty:
                continue
            print(f"  [{rtype}]  {r_df['round'].nunique()} rounds / {len(r_df)} samples")
            stats = r_df["zone"].value_counts(normalize=True).head(5)
            for zone, rate in stats.items():
                w = weights.get(zone, 1)
                icon = ICON.get(w, "[D]") if zone != "Unclassified" else "[?]"
                count = int((r_df["zone"] == zone).sum())
                print(f"    {icon}  {zone:<20} {rate*100:5.1f}%  ({count})")

    print(f"\n{sep}")


def main():
    zones   = load_zones()
    weights = load_weights()

    demo_files = glob.glob(os.path.join(DEMO_FOLDER, "*.dem"))
    if not demo_files:
        print("No .dem files in demos_analysis/")
        return

    all_records = []
    for f in demo_files:
        print(f"Parsing: {os.path.basename(f)}")
        records = parse_demo(f, zones)
        all_records.extend(records)
        print(f"  -> {len(records)} records")

    if not all_records:
        print("No data")
        return

    df = pd.DataFrame(all_records)
    print_report(df, weights)


if __name__ == "__main__":
    main()
