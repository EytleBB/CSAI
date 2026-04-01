import pandas as pd
from demoparser2 import DemoParser

# === 配置 ===
# 填入你觉得有问题的那个 Demo 路径
DEMO_PATH = r"demos_analysis\g161-n-20260123174821830606429_de_mirage.dem"


def scan_players():
    print(f"🕵️ 正在扫描 Demo 玩家名单: {DEMO_PATH} ...")
    parser = DemoParser(DEMO_PATH)

    try:
        # 我们提取第 1000 帧（比赛刚开始）和 第 50000 帧（比赛中段）的数据
        # 这样能防止漏掉中途连进来的玩家
        # 提取 name 和 steamid
        df = parser.parse_ticks(
            ["name", "steamid", "team_name"],
            ticks=[1000, 50000, 100000]
        )

        # 解包逻辑 (兼容旧版/新版解析器)
        if isinstance(df, list):
            if len(df) > 0 and isinstance(df[0], tuple):
                df = df[0][1]
            else:
                df = pd.DataFrame(df)

        if df.empty:
            print("❌ 读取失败：没有提取到玩家数据。")
            return

        # 去重：只保留唯一的玩家
        # 有时候 steamid 是字符串，有时候是数字，统一处理
        unique_players = df[['name', 'steamid']].drop_duplicates()

        print("\n" + "=" * 50)
        print(f"📋 玩家名单 (共发现 {len(unique_players)} 人)")
        print("=" * 50)
        print(f"{'Name (名字)':<25} | {'SteamID (身份证)':<20}")
        print("-" * 50)

        for _, row in unique_players.iterrows():
            name = str(row['name'])
            sid = str(row['steamid'])
            print(f"{name:<25} | {sid:<20}")

        print("=" * 50)
        print("💡 建议：")
        print("1. 请直接复制上面的【Name】到你的分析脚本里，防止有特殊符号。")
        print("2. 最稳妥的方法是改用【SteamID】来锁定玩家，因为名字会变！")

    except Exception as e:
        print(f"❌ 扫描出错: {e}")


if __name__ == "__main__":
    scan_players()