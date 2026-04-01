import os
import requests
import zipfile
import pandas as pd
from awpy import Demo  # <--- V2.0 的核心变更：使用 Demo 类

# === 配置 ===
LINK_FILE = "mirage_download_links.txt"
DEMO_DIR = "demos_analysis"


def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_demo_file():
    ensure_dir(DEMO_DIR)

    # 1. 检查目录下有没有现成的 .dem 文件
    for f in os.listdir(DEMO_DIR):
        if f.endswith(".dem"):
            print(f"📂 发现本地 Demo 文件: {f}")
            return os.path.join(DEMO_DIR, f)

    # 2. 如果没有，从 txt 读取链接下载一个
    print("🔍 本地无 Demo，准备从链接列表中下载第一个测试...")
    if not os.path.exists(LINK_FILE):
        print(f"❌ 找不到 {LINK_FILE}，请先运行 batch_link_extractor.py 生成链接文件！")
        return None

    with open(LINK_FILE, "r") as f:
        url = f.readline().strip()

    if not url:
        print("❌ 链接文件是空的。")
        return None

    zip_path = os.path.join(DEMO_DIR, "test_demo.zip")
    print(f"⬇️ 正在下载: {url}")

    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(zip_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return None

    # 3. 解压
    print("📦 正在解压...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(DEMO_DIR)
    except Exception as e:
        print(f"❌ 解压失败: {e}")
        return None

    # 找到解压后的 .dem 文件
    for f in os.listdir(DEMO_DIR):
        if f.endswith(".dem"):
            return os.path.join(DEMO_DIR, f)

    return None


def analyze_demo():
    # 1. 获取文件路径
    dem_path = get_demo_file()
    if not dem_path: return

    print(f"\n🚀 开始解析 Demo (awpy v2): {dem_path}")
    print("⏳ 正在解析中，请稍候...")

    try:
        # --- V2.0 核心代码变更 ---
        # 直接使用 Demo 类，传入文件路径
        demo = Demo(dem_path)

        # v2.0 会自动解析并在属性中提供 DataFrame
        print("\n✅ 解析成功！")
        print(f"🗺️ 地图: {demo.header.get('map_name', 'Unknown')}")
        print(f"⏱️ 总时长: {demo.header.get('playback_time', 0)} 秒")

        # --- 展示数据样例 ---

        # 1. 击杀数据 (Kills)
        # awpy v2 直接返回 DataFrame，列名通常是 snake_case (下划线命名)
        if hasattr(demo, 'kills'):
            kills_df = demo.kills
            print(f"\n🔫 [击杀数据] (共 {len(kills_df)} 条):")

            # 打印列名帮助我们确认字段
            # print(f"列名参考: {kills_df.columns.tolist()}")

            # 尝试选取常用列 (V2 的列名可能是 attacker_name 而不是 attackerName)
            # 我们先打印前几行所有列，防止列名报错
            print(kills_df.head(3).to_string(index=False))

        # 2. 回合数据 (Rounds)
        if hasattr(demo, 'rounds'):
            rounds_df = demo.rounds
            print(f"\n🏁 [回合数据] (共 {len(rounds_df)} 回合):")
            # 选取部分关键列展示
            target_cols = ['round_end_reason', 'winner_name', 'round_end_reason_label']
            available_cols = [c for c in target_cols if c in rounds_df.columns]
            print(rounds_df[available_cols].head(5).to_string(index=False))

        # 3. 投掷物数据 (Grenades)
        if hasattr(demo, 'grenades'):
            grenades_df = demo.grenades
            print(f"\n💣 [投掷物数据] (共 {len(grenades_df)} 条):")
            print(grenades_df[['thrower_name', 'grenade_type', 'x', 'y', 'z']].head(3).to_string(index=False))

        print("\n" + "=" * 40)
        print("💡 V2.0 解析成功！")
        print("现在你可以直接使用 Pandas 处理 kills_df, grenades_df 等数据了。")

    except Exception as e:
        print(f"\n❌ 解析过程中发生错误: {e}")
        print("提示: 可能是 Demo 文件损坏或 awpy 版本依赖问题。")


if __name__ == "__main__":
    analyze_demo()