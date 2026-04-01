import requests
import os

# 备选镜像源列表 (涵盖 GitHub 和 Wiki)
MIRRORS = [
    "https://raw.githubusercontent.com/liam-hogan/csgo-overviews/master/overviews/de_mirage_radar.png",
    "https://static.wikia.nocookie.net/cswikia/images/1/11/De_mirage_radar.png"
]
SAVE_PATH = "de_mirage_radar.png"


def download_map():
    print("⬇️ 正在尝试下载 Mirage 雷达图...")

    for url in MIRRORS:
        try:
            print(f"   尝试源: {url} ...")
            # 伪装 User-Agent 防止被 Wiki 拦截
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=10)

            if r.status_code == 200:
                with open(SAVE_PATH, 'wb') as f:
                    f.write(r.content)
                print(f"✅ 成功！图片已保存为: {os.path.abspath(SAVE_PATH)}")
                print("   (尺寸可能和之前预设略有不同，我们在标点时以这张图为准即可)")
                return
            else:
                print(f"   ❌ 失败 (状态码 {r.status_code})")
        except Exception as e:
            print(f"   ❌ 出错: {e}")

    print("\n⚠️ 所有自动下载都失败了。")
    print("👉 请手动操作：")
    print("1. 去百度/Google搜 'CS Mirage Radar'。")
    print(f"2. 下载一张俯视图，重命名为 '{SAVE_PATH}'。")
    print("3. 放到当前代码目录下。")


if __name__ == "__main__":
    download_map()