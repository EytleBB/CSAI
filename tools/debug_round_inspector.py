import pandas as pd
from demoparser2 import DemoParser

# === 你的 Demo 路径 ===
DEMO_PATH = r"demos_analysis\g161-n-20260123174821830606429_de_mirage.dem"


def inspect_rounds_v2():
    print(f"🩺 [V2] 正在深度扫描 Demo 结构: {DEMO_PATH} ...")
    parser = DemoParser(DEMO_PATH)

    # 1. 提取关键事件
    # 我们需要这三个事件来理清：热身、正式开始、每一回合
    target_events = ["round_start", "round_announce_match_start", "round_freeze_end"]

    try:
        raw_output = parser.parse_events(target_events, other=["tick"])
    except Exception as e:
        print(f"❌ 解析器报错: {e}")
        return

    # 2. 核心修复：正确的数据合并逻辑
    all_dfs = []

    # 检查返回结构
    if isinstance(raw_output, list):
        for item in raw_output:
            # 标准结构是 tuple: (event_name, dataframe)
            if isinstance(item, tuple) and len(item) == 2:
                evt_name = item[0]
                df_part = item[1]

                # 关键步骤：手动给这个小表格贴上标签！
                df_part['event_name'] = evt_name
                all_dfs.append(df_part)

    if not all_dfs:
        print("❌ 未提取到任何事件数据 (Demo可能损坏或版本不兼容)")
        return

    # 合并成一张大表
    df_master = pd.concat(all_dfs, ignore_index=True)
    # 按时间排序，还原真实发生顺序
    df_master = df_master.sort_values(by='tick')

    # 3. 打印流水账
    print("\n" + "=" * 80)
    print(f"{'Tick (时间点)':<12} | {'Event Name (发生了什么)':<30} | {'逻辑判定'}")
    print("=" * 80)

    round_counter = 0
    match_live = False  # 比赛是否正式开始

    for _, row in df_master.iterrows():
        tick = row['tick']
        evt = row['event_name']
        note = ""

        # A. 比赛正式开始信号
        if evt == "round_announce_match_start":
            match_live = True
            round_counter = 0  # 重置计数器！之前的都是热身！
            note = "🔥 --- [MATCH LIVE / 热身结束] --- 🔥"
            print("-" * 80)

        # B. 回合开始信号
        elif evt == "round_start":
            if match_live:
                round_counter += 1
                note = f"✅ 第 {round_counter} 回合开始"
            else:
                note = "💤 热身阶段 (Warmup Round)"

        # C. 冻结时间结束 (买完枪了)
        elif evt == "round_freeze_end":
            if match_live:
                note = "   🛒 冻结结束 (准备检测经济)"
            else:
                note = "   💤 热身冻结结束"

        print(f"{tick:<12} | {evt:<30} | {note}")

    print("=" * 80)

    # 4. 重点诊断：手枪局经济
    # 我们找到“比赛正式开始”后的第一个 freeze_end
    print("\n💰 [手枪局侦探] 正在核实第 1 回合的 CT 资产...")

    # 筛选出正式开始后的冻结结束点
    match_start_tick = 0
    start_events = df_master[df_master['event_name'] == 'round_announce_match_start']
    if not start_events.empty:
        match_start_tick = start_events.iloc[-1]['tick']

    real_freeze_ticks = df_master[
        (df_master['event_name'] == 'round_freeze_end') &
        (df_master['tick'] > match_start_tick)
        ]['tick'].tolist()

    if real_freeze_ticks:
        # 取前两个回合看看
        check_ticks = real_freeze_ticks[:2]

        # 查钱
        money_data = parser.parse_ticks(["m_iCurrentEqValue", "team_name"], ticks=check_ticks)
        df_money = pd.DataFrame()
        if isinstance(money_data, list) and len(money_data) > 0: df_money = money_data[0][1]

        for i, tick in enumerate(check_ticks):
            ct_rows = df_money[(df_money['tick'] == tick) & (df_money['team_name'] == 'CT')]
            total_val = ct_rows['m_iCurrentEqValue'].sum()

            print(f"   👉 第 {i + 1} 回合 (Tick {tick}): CT全队资产 = ${total_val}")

            if 3500 <= total_val <= 5000:
                print("      ✅ 判定：这就是标准手枪局！")
            elif total_val > 10000:
                print("      ❌ 判定：这是长枪局 (或者还在热身？)")
            else:
                print("      ❓ 判定：经济很奇怪")
    else:
        print("❌ 没找到正式开始后的冻结结束点。")


if __name__ == "__main__":
    inspect_rounds_v2()