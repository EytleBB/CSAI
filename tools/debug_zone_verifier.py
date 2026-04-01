import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
import json
import pandas as pd
from demoparser2 import DemoParser
import os

# === 配置 ===
ZONES_FILE = "mirage_zones.json"
# 随便填一个有效的 Demo
DEMO_PATH = r"demos_analysis\g161-n-20260123174821830606429_de_mirage.dem"
TARGET_PLAYER = "Liminus"  # 换成一个你确定上场了的玩家


def verify_zones():
    print("🕵️ 启动上帝视角验证...")

    # 1. 读取你画的区域 (JSON)
    if not os.path.exists(ZONES_FILE):
        print("❌ 找不到 zones 文件")
        return
    with open(ZONES_FILE, 'r', encoding='utf-8') as f:
        zones_data = json.load(f)
    print(f"✅ 加载了 {len(zones_data)} 个区域")

    # 2. 读取玩家真实轨迹 (Demo)
    print("extracting player trajectory...")
    parser = DemoParser(DEMO_PATH)

    # 提取全场位置
    try:
        # 为了速度，每 64 tick 采一个点
        max_tick = parser.parse_event("round_end")["tick"].max()
        ticks = list(range(0, int(max_tick), 64))

        df = parser.parse_ticks(["X", "Y", "name", "team_name"], ticks=ticks)
        # 解包
        if isinstance(df, list):
            df = df[0][1]
        else:
            df = pd.DataFrame(df)

        # 筛选玩家
        player_df = df[df['name'] == TARGET_PLAYER]
        if player_df.empty:
            print(f"❌ 没找到玩家 {TARGET_PLAYER}，改用全场所有玩家数据...")
            player_df = df  # 找不到就画所有人，不管了

        print(f"✅ 提取了 {len(player_df)} 个轨迹点")

    except Exception as e:
        print(f"❌ Demo 读取失败: {e}")
        return

    # 3. 绘图 (不带地图背景，纯数据)
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.set_title(f"DEBUG: Zones (Blue) vs Player Trace (Red)\nPlayer: {TARGET_PLAYER}")

    # 画区域 (Blue Polygons)
    for name, coords in zones_data.items():
        # coords is [[x,y], [x,y]...]
        poly = MplPolygon(coords, closed=True, edgecolor='blue', facecolor='cyan', alpha=0.3, label='Zone')
        ax.add_patch(poly)
        # 标名字
        cx = sum(p[0] for p in coords) / len(coords)
        cy = sum(p[1] for p in coords) / len(coords)
        ax.text(cx, cy, name, color='blue', fontsize=8, ha='center', weight='bold')

    # 画轨迹 (Red Dots)
    ax.scatter(player_df['X'], player_df['Y'], s=2, c='red', alpha=0.5, label='Trace')

    # 强制等比例 (这很重要，否则会被拉伸掩盖问题)
    ax.axis('equal')
    ax.grid(True)

    # 自动调整视野包含所有数据
    all_x = list(player_df['X'])
    all_y = list(player_df['Y'])
    for coords in zones_data.values():
        for p in coords:
            all_x.append(p[0])
            all_y.append(p[1])

    if all_x:
        ax.set_xlim(min(all_x) - 500, max(all_x) + 500)
        ax.set_ylim(min(all_y) - 500, max(all_y) + 500)

    print("👉 请观察图片：")
    print("1. 红色的轨迹线（玩家走的路）是否穿过了蓝色的区域？")
    print("2. 还是说它们彻底分离了？或者呈镜像反转？")
    plt.show()


if __name__ == "__main__":
    verify_zones()