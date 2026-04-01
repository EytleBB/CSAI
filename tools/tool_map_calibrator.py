import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import pandas as pd
from demoparser2 import DemoParser
import os
import json

# === 配置 ===
# 使用原本的图片
MAP_IMG_PATH = "de_mirage_radar.png"
# 随便找一个 Demo 用来提取真实坐标
DEMO_PATH = r"demos_analysis\g161-n-20260123174821830606429_de_mirage.dem"
# 输出的新配置文件
CONFIG_FILE = "map_config.json"

# 默认参数 (作为起点)
INITIAL_CONFIG = {
    "pos_x": -3230,
    "pos_y": 1713,
    "scale": 5.0
}


def run_calibrator():
    print("🚀 启动地图校准器...")
    print("1. 读取 Demo 位置数据...")

    parser = DemoParser(DEMO_PATH)
    # 提取全场所有位置 (每隔 128 tick 采一次样，这就够画出轮廓了)
    max_tick = parser.parse_event("round_end")["tick"].max()
    ticks = list(range(0, int(max_tick), 128))

    try:
        df = parser.parse_ticks(["X", "Y"], ticks=ticks)
        if isinstance(df, list): df = df[0][1]  # 兼容性处理
        # 转换为 DataFrame
        df = pd.DataFrame(df)
        print(f"✅ 提取到 {len(df)} 个坐标点")
    except Exception as e:
        print(f"❌ 读取 Demo 失败: {e}")
        return

    print("2. 启动可视化界面...")

    # 加载图片
    if not os.path.exists(MAP_IMG_PATH):
        print("❌ 找不到图片")
        return
    img = plt.imread(MAP_IMG_PATH)
    img_height, img_width = img.shape[:2]

    # 创建窗口
    fig, ax = plt.subplots(figsize=(12, 10))
    plt.subplots_adjust(left=0.1, bottom=0.35)  # 留出底部给滑块

    # 显示图片 (Extent 决定了图片在坐标系里的位置)
    # 我们不动图片，我们动“坐标系”
    # 但为了直观，我们反过来：根据参数计算图片应该铺在哪里

    def get_extent(pos_x, pos_y, scale):
        # CS2 雷达图逻辑:
        # TopLeft_Game_X = pos_x
        # TopLeft_Game_Y = pos_y
        # BottomRight_Game_X = pos_x + (width * scale)
        # BottomRight_Game_Y = pos_y - (height * scale)
        return [
            pos_x,
            pos_x + (img_width * scale),
            pos_y - (img_height * scale),
            pos_y
        ]

    # 初始绘图
    # 1. 画真实的 Demo 点 (绿色)
    # zorder=2 保证点在图上面
    scatter = ax.scatter(df['X'], df['Y'], s=1, c='#00ff00', alpha=0.5, label='Demo Data', zorder=2)

    # 2. 画地图图片 (底层)
    # extent=[left, right, bottom, top]
    extent = get_extent(INITIAL_CONFIG["pos_x"], INITIAL_CONFIG["pos_y"], INITIAL_CONFIG["scale"])
    map_layer = ax.imshow(img, extent=extent, zorder=1, alpha=0.7)

    ax.set_title("Map Calibrator: Align Green Dots to Map Image")
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.2)

    # === 滑块区域 ===
    ax_x = plt.axes([0.15, 0.20, 0.65, 0.03])
    ax_y = plt.axes([0.15, 0.15, 0.65, 0.03])
    ax_s = plt.axes([0.15, 0.10, 0.65, 0.03])

    # 范围设大一点，方便拖动
    s_x = Slider(ax_x, 'Pos X', -5000, 0, valinit=INITIAL_CONFIG["pos_x"])
    s_y = Slider(ax_y, 'Pos Y', 0, 5000, valinit=INITIAL_CONFIG["pos_y"])
    s_scale = Slider(ax_s, 'Scale', 1.0, 10.0, valinit=INITIAL_CONFIG["scale"])

    # 更新函数
    def update(val):
        new_x = s_x.val
        new_y = s_y.val
        new_scale = s_scale.val

        # 更新图片的显示范围
        new_extent = get_extent(new_x, new_y, new_scale)
        map_layer.set_extent(new_extent)

        # 重新自动缩放视图，确保能看到全部
        # ax.relim()
        # ax.autoscale_view()
        fig.canvas.draw_idle()

    s_x.on_changed(update)
    s_y.on_changed(update)
    s_scale.on_changed(update)

    # === 保存按钮 ===
    save_ax = plt.axes([0.8, 0.025, 0.1, 0.04])
    btn_save = Button(save_ax, 'Save Config', hovercolor='0.975')

    def save(event):
        config = {
            "pos_x": float(s_x.val),
            "pos_y": float(s_y.val),
            "scale": float(s_scale.val)
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"\n✅ 校准参数已保存至 {CONFIG_FILE}")
        print(json.dumps(config, indent=4))
        print("👉 重要：请现在重新运行 map_zone_editor_v4.py，你会发现旧的圈歪了，请【删除旧JSON并重新画】！")

    btn_save.on_clicked(save)

    print("\n💡 操作指南：")
    print("1. 拖动 [Scale] 让地图大小和绿色点阵大小一致。")
    print("2. 拖动 [Pos X] 和 [Pos Y] 平移地图，让它们重合。")
    print("3. 绿色点阵是真实的玩家足迹，它们应该完美落在地图的道路上。")
    print("4. 对齐后点击右下角 [Save Config]。")

    plt.show()


if __name__ == "__main__":
    run_calibrator()