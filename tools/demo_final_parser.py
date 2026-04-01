import os
import pandas as pd  # <--- 换回 Pandas，它更宽容
from demoparser2 import DemoParser

# Demo 路径
DEMO_PATH = r"demos_analysis\g161-n-20260123174821830606429_de_mirage.dem"


def parse_final():
    print(f"🧹 启动最终清洗模式... 目标: {DEMO_PATH}")

    if not os.path.exists(DEMO_PATH):
        print("❌ 文件不存在")
        return

    try:
        # 1. 初始化解析器
        parser = DemoParser(DEMO_PATH)
        header = parser.parse_header()
        print(f"✅ 地图: {header.get('map_name')} | 客户端: {header.get('client_name')}")

        # 2. 提取核心事件：击杀 (player_death)
        # 5E 的 Demo 可能包含非常丰富的数据，我们只取我们关心的
        print("\n🔍 正在提取击杀数据...")

        # event_name: player_death
        # 我们还可以提取: round_end, player_hurt, bomb_planted 等
        events = parser.parse_events(["player_death"])

        # --- 核心修复：使用 Pandas 转换，自动处理 NaN ---
        df = pd.DataFrame(events)

        # 3. 数据清洗与展示
        if not df.empty:
            print(f"✅ 成功提取 {len(df)} 条击杀记录！")

            # 筛选算法分析最有用的列
            # user_X/Y 是受害者坐标, attacker_X/Y 是凶手坐标
            target_cols = [
                'tick',
                'attacker_name', 'user_name',  # 凶手 vs 受害者
                'weapon', 'is_headshot',  # 武器与爆头
                'attacker_X', 'attacker_Y',  # 凶手位置 (做热力图用)
                'user_X', 'user_Y',  # 受害者位置
                'assistedflash'  # 是否被闪光辅助
            ]

            # 过滤掉不存在的列（防止报错）
            valid_cols = [c for c in target_cols if c in df.columns]

            # 打印前 10 条数据
            print("\n📊 [击杀数据预览 - 算法准备就绪]")
            print(df[valid_cols].head(10).to_string(index=False))

            # 4. 提取每一帧的玩家位置 (Tick Data) - 这是最高级算法需要的
            print("\n🔍 正在尝试提取第 10000 帧的玩家位置 (测试 Tick 数据)...")
            try:
                # 这是一个重型操作，我们只取一帧测试一下
                ticks = parser.parse_ticks(["X", "Y", "Z", "view_X", "view_Y"], ticks=[10000])
                tick_df = pd.DataFrame(ticks)
                print(f"✅ Tick 数据提取成功！包含 {len(tick_df)} 条记录 (对应场上10名玩家)")
                print(tick_df[['steamid', 'name', 'X', 'Y', 'Z']].head().to_string(index=False))
            except Exception as e:
                print(f"⚠️ Tick 数据提取跳过: {e}")

            print("\n" + "=" * 40)
            print("🎉 完美！数据已就绪。")
            print("我们可以开始写算法了：")
            print("1. 根据 attacker_X/Y -> 绘制热力图")
            print("2. 根据 weapon + is_headshot -> 分析枪法水平")
            print("3. 根据 tick 轨迹 -> 分析默认站位")

        else:
            print("❌ 解析结果为空，真奇怪。")

    except Exception as e:
        print(f"❌ 发生错误: {e}")


if __name__ == "__main__":
    parse_final()