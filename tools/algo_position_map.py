import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from demoparser2 import DemoParser

# Demo 路径 (沿用你刚才成功的路径)
DEMO_PATH = r"demos_analysis\g161-n-20260123174821830606429_de_mirage.dem"
OUTPUT_IMG = "position_map.png"


def run_position_analysis():
    print(f"🎨 启动算法分析：位置热点图...")

    if not os.path.exists(DEMO_PATH):
        print("❌ 找不到 Demo 文件")
        return

    parser = DemoParser(DEMO_PATH)

    # --- 1. 诊断击杀数据的列名 (为了修复上一步的空白) ---
    print("\n🔍 [诊断] 正在读取击杀事件列名...")
    death_events = parser.parse_events(["player_death"])
    death_df = pd.DataFrame(death_events)
    if not death_df.empty:
        print(f"   ✅ 击杀表包含列: {list(death_df.columns)}")
        # 顺便看看有没有我们要的 'attacker_name'
        if 'attacker_name' in death_df.columns:
            print("   🆗 确认包含 'attacker_name'")
    else:
        print("   ⚠️ 击杀表依然为空 (可能是Demo本身只有跑图没有击杀)")

    # --- 2. 提取高频位置数据 (Tick Data) ---
    print("\n🔍 [算法] 正在提取全员位置数据...")
    print("   (为了速度，我们每隔 128 帧采样一次，相当于每秒取一个点)")

    # 获取最大 tick
    max_tick = parser.parse_event("round_end")["tick"].max() if "tick" in parser.parse_event(
        "round_end").columns else 100000

    # 构建采样点：每 128 tick 取一次
    wanted_ticks = list(range(0, int(max_tick), 128))

    try:
        # 提取 X, Y 坐标
        ticks_data = parser.parse_ticks(["X", "Y", "name", "team_name"], ticks=wanted_ticks)
        df = pd.DataFrame(ticks_data)

        print(f"   ✅ 提取成功！共 {len(df)} 个坐标点")
        print(df.head(3))

        # --- 3. 绘制散点图 (Matplotlib) ---
        print(f"\n🎨 正在绘制位置分布图...")

        plt.figure(figsize=(10, 10))
        plt.style.use('dark_background')  # 使用暗色背景，更有CS风格

        # 使用 Seaborn 绘制散点
        # hue='name' 会给不同玩家上不同颜色
        # alpha=0.6 让点由透明度，重叠的地方会变亮（形成类似热力图的效果）
        sns.scatterplot(
            data=df,
            x='X',
            y='Y',
            hue='name',
            palette='tab10',
            s=10,
            alpha=0.6,
            legend=False  # 玩家太多，先不显示图例，避免遮挡
        )

        plt.title(f"Player Positions Analysis - {os.path.basename(DEMO_PATH)}", color='white')
        plt.axis('equal')  # 保证 X 和 Y 轴比例一致，地图才不会变形
        plt.grid(False)

        # 保存图片
        plt.savefig(OUTPUT_IMG, dpi=150, bbox_inches='tight')
        print(f"🎉 图片已保存: {os.path.abspath(OUTPUT_IMG)}")
        print("👉 请打开这张图片！你应该能看到由点组成的 Mirage 地图轮廓！")

    except Exception as e:
        print(f"❌ 绘图失败: {e}")


if __name__ == "__main__":
    run_position_analysis()