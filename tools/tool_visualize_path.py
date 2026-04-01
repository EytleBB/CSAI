import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from demoparser2 import DemoParser
import json
import os
import glob

# === ⚙️ 配置 ===
DEMO_FOLDER = r"demos_analysis"
TARGET_NAME_KEYWORD = "cs智者"

MAP_IMG = "de_mirage_radar.png"
ZONES_FILE = "mirage_zones.json"
CONFIG_FILE = "map_config.json"


class PathVisualizerNuclear:
    def __init__(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                self.cfg = json.load(f)
        else:
            self.cfg = {"pos_x": -3230, "pos_y": 1713, "scale": 5.0}

        self.zones = {}
        if os.path.exists(ZONES_FILE):
            with open(ZONES_FILE, 'r', encoding='utf-8') as f:
                self.zones = json.load(f)

    def game_to_pixel(self, gx, gy):
        px = (gx - self.cfg["pos_x"]) / self.cfg["scale"]
        py = (self.cfg["pos_y"] - gy) / self.cfg["scale"]
        return px, py

    def run(self):
        files = glob.glob(os.path.join(DEMO_FOLDER, "*.dem"))
        if not files:
            print("❌ 没有 Demo 文件")
            return
        demo_path = files[0]
        print(f"🎬 正在解析: {os.path.basename(demo_path)}")
        parser = DemoParser(demo_path)

        # === 1. 锁定 Round 1 ===
        print("1. 正在锁定手枪局时间...")
        try:
            raw_events = parser.parse_events(["round_announce_match_start", "round_freeze_end", "round_end"],
                                             other=["tick"])
            all_dfs = []
            if isinstance(raw_events, list):
                for item in raw_events:
                    if isinstance(item, tuple) and len(item) == 2:
                        df_part = item[1]
                        df_part['event_name'] = item[0]
                        all_dfs.append(df_part)

            if not all_dfs: raise Exception("事件为空")
            df_evts = pd.concat(all_dfs, ignore_index=True).sort_values('tick')

            match_start_tick = 0
            start_sig = df_evts[df_evts['event_name'] == "round_announce_match_start"]
            if not start_sig.empty: match_start_tick = start_sig.iloc[-1]['tick']

            freeze_ends = df_evts[(df_evts['event_name'] == 'round_freeze_end') & (df_evts['tick'] > match_start_tick)]
            if freeze_ends.empty: raise Exception("找不到回合开始")
            r1_start = freeze_ends.iloc[0]['tick']

            r1_ends = df_evts[(df_evts['event_name'] == 'round_end') & (df_evts['tick'] > r1_start)]
            r1_end = r1_ends.iloc[0]['tick'] if not r1_ends.empty else r1_start + 10000

            print(f"   ✅ 锁定 R1 区间: {r1_start} -> {r1_end}")

        except Exception as e:
            print(f"   ⚠️ 自动锁定失败 ({e})，尝试绘制全场数据作为兜底...")
            r1_start = 0
            r1_end = 200000

        # === 2. 核弹级数据提取 (多方案轮询) ===
        print("2. 正在尝试多重提取方案...")

        # 方案定义
        STRATEGIES = [
            {"name": "A (完整)", "cols": ["X", "Y", "name", "team_name", "active_weapon_name"]},
            {"name": "B (标准)", "cols": ["X", "Y", "name", "team_name"]},
            {"name": "C (保底)", "cols": ["X", "Y", "name"]}  # 只要名字和位置，啥都不要了
        ]

        df_all = pd.DataFrame()

        # 获取最大 tick
        try:
            header = parser.parse_header(); max_tick = int(header.get("playback_ticks", 200000))
        except:
            max_tick = 200000

        # 轮询方案
        for strat in STRATEGIES:
            print(f"   👉 尝试方案 {strat['name']}...")
            try:
                # 关键：使用 range 全读，步长 64
                raw = parser.parse_ticks(strat['cols'], ticks=range(0, max_tick, 64))

                temp_df = pd.DataFrame()
                if isinstance(raw, list) and len(raw) > 0:
                    if isinstance(raw[0], tuple):
                        temp_df = raw[0][1]
                    else:
                        temp_df = pd.DataFrame(raw)

                if not temp_df.empty:
                    df_all = temp_df
                    print(f"      ✅ 成功！提取到 {len(df_all)} 行数据")
                    break  # 成功就退出循环
                else:
                    print("      ❌ 返回空数据")
            except Exception as e:
                print(f"      ❌ 报错: {e}")

        if df_all.empty:
            print("❌ 所有提取方案均失败。Demo 文件可能已损坏或被加密。")
            return

        # === 3. 筛选与绘图 ===
        print("3. 正在筛选 cs智者 的 R1 数据...")

        # 名字筛选
        df_target = df_all[df_all['name'].astype(str).str.contains(TARGET_NAME_KEYWORD, case=False, na=False)].copy()

        # 时间筛选
        df_target = df_target[(df_target['tick'] >= r1_start) & (df_target['tick'] <= r1_end)]

        if df_target.empty:
            print(f"❌ 未找到玩家 '{TARGET_NAME_KEYWORD}' 的数据")
            return

        # 获取信息
        full_name = df_target.iloc[0]['name']
        team = "Unknown"
        if 'team_name' in df_target.columns:
            team = df_target.iloc[0]['team_name']

        print(f"   ✅ 准备绘图: {full_name} ({team}) - {len(df_target)} 个点")

        # 绘图
        if not os.path.exists(MAP_IMG): print("❌ 缺图"); return
        img = plt.imread(MAP_IMG)

        fig, ax = plt.subplots(figsize=(10, 10))
        ax.imshow(img)
        ax.set_title(f"R1 Path: {full_name} ({team})", fontsize=14, weight='bold', color='white',
                     backgroundcolor='black')

        # 画区域
        for z_name, coords in self.zones.items():
            pixel_poly = [self.game_to_pixel(p[0], p[1]) for p in coords]
            poly = MplPolygon(pixel_poly, closed=True, edgecolor='white', facecolor='cyan', alpha=0.15)
            ax.add_patch(poly)
            cx = sum(p[0] for p in pixel_poly) / len(pixel_poly)
            cy = sum(p[1] for p in pixel_poly) / len(pixel_poly)
            ax.text(cx, cy, z_name, color='white', fontsize=6, ha='center', alpha=0.5)

        # 画轨迹
        xs, ys = [], []
        for _, row in df_target.iterrows():
            px, py = self.game_to_pixel(row['X'], row['Y'])
            xs.append(px)
            ys.append(py)

        c = 'cyan' if team == 'CT' else 'gold'
        if team == 'Unknown': c = 'lime'

        ax.plot(xs, ys, color=c, linewidth=2.5, alpha=0.9, label=f'Path')
        ax.scatter(xs[0], ys[0], c='white', s=100, edgecolors='black', zorder=5, label='Start')
        ax.scatter(xs[-1], ys[-1], c='red', s=100, marker='X', edgecolors='black', zorder=5, label='End')

        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    PathVisualizerNuclear().run()