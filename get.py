import requests
import re
import time


def get_and_clean_elf_data():
    # ================= 配置区域 =================
    API_URL = "https://wiki.biligame.com/rocom/api.php"
    BASE_URL = "https://wiki.biligame.com/rocom/"
    OUTPUT_FILE = "elf_list.txt"

    # 需要排除的非精灵关键词
    EXCLUDE_KEYWORDS = ["道具", "技能", "攻略", "地图", "任务", "活动", "模板", "分类", "用户", "帮助", "文件"]

    # ================= 1. 获取数据 =================
    print(">>> 正在通过 API 获取原始数据...")
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:精灵",
        "cmlimit": "500",
        "cmtype": "page",
        "format": "json"
    }

    all_pages = []
    while True:
        try:
            response = requests.get(API_URL, params=params, timeout=10)
            data = response.json()
            pages = data['query']['categorymembers']
            all_pages.extend(pages)

            if 'continue' in data:
                params.update(data['continue'])
            else:
                break
        except Exception as e:
            print(f"请求出错: {e}")
            break

    print(f"API 获取完成，原始数据共 {len(all_pages)} 条")

    # ================= 2. 清洗与去重 =================
    print(">>> 正在清洗数据（去重、去形态）...")

    # 字典用于去重：Key是基础名，Value是完整信息
    elf_dict = {}

    for page in all_pages:
        title = page['title']

        # 2.1 排除非精灵页面
        if any(keyword in title for keyword in EXCLUDE_KEYWORDS):
            continue
        if '/' in title:  # 排除子页面
            continue

        # 2.2 提取基础名称（去除括号内容）
        # 正则 r'（.*?）' 匹配中文括号及其内容
        # 比如 "丢丢（火山）" -> "丢丢"
        base_name = re.sub(r'（.*?）', '', title)

        # 2.3 核心去重逻辑
        # 如果这个基础名还没在字典里，就存入
        # 如果已经在字典里，说明已经有了（可能是无括号的原版，也可能是之前的形态）
        # 这里我们优先保留“短”的名字，或者你可以认为先遇到的就是主要的
        if base_name not in elf_dict:
            elf_dict[base_name] = {
                "name": base_name,
                "url": BASE_URL + title.replace(' ', '_')  # 使用原始标题构建URL（防止链接失效）
            }

    # 转换为列表并排序
    final_list = list(elf_dict.values())
    final_list.sort(key=lambda x: x['name'])  # 按名称排序

    print(f"清洗完成，最终有效精灵数量: {len(final_list)}")

    # ================= 3. 保存到文件 =================
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for item in final_list:
                f.write(f"{item['url']}\n")
        print(f"✅ 成功！数据已保存至 {OUTPUT_FILE}")

        # 打印前10个预览
        print("\n--- 前 10 个预览 ---")
        for item in final_list[:10]:
            print(item['url'])

    except Exception as e:
        print(f"保存文件时出错: {e}")


if __name__ == "__main__":
    get_and_clean_elf_data()