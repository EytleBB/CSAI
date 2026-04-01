"""
诊断脚本：检查玩家为什么没有 Mirage demo 可用
只做 API 查询，不下载任何文件
用法: python debug_api_diagnose.py
"""
import requests
import urllib3
urllib3.disable_warnings()

ARENA = "https://arena.5eplay.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0"}
TIMEOUT = 15

USERNAMES = ["emooQAQ", "浮世唯", "1015_", "holyhao", "Alluwantpeek"]


def search_player(username):
    url = f"{ARENA}/api/search?keywords={requests.utils.quote(username)}"
    r = requests.get(url, timeout=TIMEOUT, verify=False, headers=HEADERS)
    d = r.json()
    users = d.get("data", {}).get("user", {}).get("list", [])
    if not users:
        return None, None
    return users[0]["domain"], users[0]["username"]


def probe_domain(domain):
    """尝试所有 match_type，返回每种结果概要"""
    results = {}
    for candidate in ["", "?match_type=9", "?match_type=1", "?match_type=8",
                      "?match_type=2", "?match_type=3", "?match_type=5"]:
        try:
            url = f"{ARENA}/api/data/player/{domain}{candidate}"
            r = requests.get(url, timeout=TIMEOUT, verify=False, headers=HEADERS)
            j = r.json()
            matches = j.get("match", [])
            if not matches:
                results[candidate or "(no param)"] = "无 match 字段或空"
                continue

            # 统计各地图数量和 demo_url 情况
            map_counts = {}
            mirage_with_demo = 0
            mirage_no_demo = 0
            for m in matches:
                mp = m.get("map", "unknown")
                map_counts[mp] = map_counts.get(mp, 0) + 1
                if mp == "de_mirage":
                    if m.get("demo_url"):
                        mirage_with_demo += 1
                    else:
                        mirage_no_demo += 1

            results[candidate or "(no param)"] = {
                "total_matches_on_page1": len(matches),
                "map_distribution": dict(sorted(map_counts.items(), key=lambda x: -x[1])),
                "mirage_with_demo_url": mirage_with_demo,
                "mirage_no_demo_url": mirage_no_demo,
            }
        except Exception as e:
            results[candidate or "(no param)"] = f"ERROR: {e}"
    return results


def main():
    for username in USERNAMES:
        print(f"\n{'='*60}")
        print(f"玩家: {username}")
        print("="*60)

        domain, matched = search_player(username)
        if not domain:
            print("  ❌ 搜索失败：5E 上未找到该玩家")
            continue
        print(f"  ✓ 找到: matched_name={matched!r}, domain={domain}")

        probe = probe_domain(domain)
        for param, info in probe.items():
            if isinstance(info, dict):
                maps = info["map_distribution"]
                mirage_d = info["mirage_with_demo_url"]
                mirage_nd = info["mirage_no_demo_url"]
                top_maps = ", ".join(f"{k}({v})" for k, v in list(maps.items())[:5])
                status = ""
                if mirage_d > 0:
                    status = f"✓ {mirage_d} 个 Mirage demo 可用"
                elif mirage_nd > 0:
                    status = f"⚠ {mirage_nd} 个 Mirage 局但 demo_url 为空"
                elif "de_mirage" not in maps:
                    status = "✗ 该页无 Mirage 局"
                print(f"  [{param:20s}] 共{info['total_matches_on_page1']}场 | 地图: {top_maps} | {status}")
            else:
                print(f"  [{param:20s}] {info}")


if __name__ == "__main__":
    main()
