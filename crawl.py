#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
洛克王国手游精灵数据爬虫
功能：批量抓取所有精灵的属性、种族值和可学技能，导出为 CSV 文件
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import json
from urllib.parse import quote, unquote

# 基础 URL
BASE_URL = "https://wiki.biligame.com/rocom/"
POKEDEX_URL = "https://wiki.biligame.com/rocom/精灵图鉴"

# 请求头，模拟浏览器
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def get_all_pokemon_links():
    """
    从精灵图鉴页面获取所有精灵的链接和名称
    返回：[(精灵名，URL), ...]
    """
    print("正在获取精灵图鉴列表...")

    try:
        response = requests.get(POKEDEX_URL, headers=HEADERS, timeout=30)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        pokemon_list = []

        # 查找所有精灵卡片链接
        # 根据页面结构，精灵链接在图鉴页面中
        links = soup.find_all('a', href=True)

        for link in links:
            href = link['href']
            # 过滤出精灵详情页链接
            if '/rocom/' in href and not any(x in href for x in ['分类:', '特殊:', 'index.php']):
                # 提取精灵名
                pokemon_name = href.split('/rocom/')[-1]
                # 排除非精灵页面
                if pokemon_name not in ['首页', '精灵图鉴', '大地图', '地图']:
                    full_url = f"https://wiki.biligame.com{href}" if href.startswith('/') else href
                    pokemon_list.append((pokemon_name, full_url))

        # 去重
        pokemon_list = list(set(pokemon_list))
        print(f"共找到 {len(pokemon_list)} 个精灵")

        return pokemon_list

    except Exception as e:
        print(f"获取精灵列表失败：{e}")
        return []


def parse_pokemon_detail(url, pokemon_name):
    """
    解析精灵详情页面，提取属性、种族值和技能信息
    返回：dict 包含所有信息
    """
    result = {
        '编号': '',
        '名称': pokemon_name,
        '属性': '',
        '种族值总和': '',
        '生命': '',
        '物攻': '',
        '魔攻': '',
        '物防': '',
        '魔防': '',
        '速度': '',
        '特性名称': '',
        '特性描述': '',
        '技能列表': ''  # JSON 字符串存储所有技能
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 获取页面文本内容
        text_content = soup.get_text(separator='\n', strip=True)
        lines = text_content.split('\n')

        # 1. 提取编号和名称
        for i, line in enumerate(lines):
            # 匹配 "NO005.火花" 格式
            match = re.match(r'NO(\d+)\.(.+)', line.strip())
            if match:
                result['编号'] = f"NO{match.group(1)}"
                result['名称'] = match.group(2).strip()
                break

        # 2. 提取属性（在编号行附近）
        # 通常属性是单个汉字，在编号之后
        for i, line in enumerate(lines):
            if result['编号'] in line:
                # 属性通常在下一行或下几行
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].strip() in ['火', '水', '草', '电', '冰', '龙', '光', '暗', '毒', '虫', '武', '翼',
                                            '萌', '幽', '恶', '机械', '幻', '普通', '地']:
                        result['属性'] = lines[j].strip()
                        break
                break

        # 3. 提取种族值
        race_stats = {'生命': '', '物攻': '', '魔攻': '', '物防': '', '魔防': '', '速度': ''}
        stat_names = ['生命', '物攻', '魔攻', '物防', '魔防', '速度']

        for i, line in enumerate(lines):
            if '种族值' in line:
                # 种族值总和可能在下一行
                if i + 1 < len(lines) and lines[i + 1].strip().isdigit():
                    result['种族值总和'] = lines[i + 1].strip()

                # 提取各项种族值
                for j in range(i, min(i + 20, len(lines))):
                    if lines[j].strip() in stat_names:
                        stat_name = lines[j].strip()
                        # 数值在下一行
                        if j + 1 < len(lines) and lines[j + 1].strip().isdigit():
                            race_stats[stat_name] = lines[j + 1].strip()

                # 更新结果
                result.update(race_stats)
                break

        # 4. 提取特性（修复：更宽松的匹配，不依赖"使用"关键字）
        trait_pattern = re.compile(r'特性[：:]\s*(.+)')
        for i, line in enumerate(lines):
            # 尝试匹配 "特性: xxx" 或 "特性 xxx" 格式
            match = trait_pattern.search(line)
            if match:
                result['特性名称'] = match.group(1).strip()
                break

        # 提取特性描述：从"特性"行向后搜索，找到包含描述性内容的行
        for i, line in enumerate(lines):
            if '特性' in line and '特性' == line.strip()[:2]:
                # 跳过标题行，向后搜索描述内容
                for j in range(i + 1, min(i + 10, len(lines))):
                    candidate = lines[j].strip()
                    # 描述通常是有内容的句子，不为空且不以"特性"开头
                    if candidate and len(candidate) > 5 and '特性' not in candidate[:2]:
                        result['特性描述'] = candidate
                        break
                break

        # 5. 提取技能列表
        skills = []
        skill_keywords = ['猛烈撞击', '火苗', '火焰切割', '防御', '吹火', '晒太阳', '怒火', '火云车', '热身', '闪燃',
                          '山火',
                          '力量增效', '持续高温', '撞击', '抓', '火花', '水枪', '泡沫', '藤鞭', '种子机关枪']

        # 查找技能部分
        in_skill_section = False
        current_skill = {}

        for i, line in enumerate(lines):
            line = line.strip()

            # 检测技能等级行（LV 开头）
            lv_match = re.match(r'LV(\d+)', line)
            if lv_match:
                # 保存之前的技能
                if current_skill and '名称' in current_skill:
                    skills.append(current_skill)

                current_skill = {
                    '等级': int(lv_match.group(1)),
                    '名称': '',
                    'PP': '',
                    '类型': '',
                    '威力': '',
                    '描述': ''
                }
                in_skill_section = True

                # 技能名在下一行
                if i + 1 < len(lines):
                    current_skill['名称'] = lines[i + 1].strip()

            elif in_skill_section and current_skill:
                # PP 值（数字）
                if line.isdigit() and not current_skill['PP']:
                    current_skill['PP'] = line
                # 技能类型
                elif line in ['物攻', '魔攻', '状态', '防御']:
                    current_skill['类型'] = line
                # 威力
                elif line.isdigit() and not current_skill['威力'] and current_skill['类型']:
                    current_skill['威力'] = line
                # 描述（以✦开头）
                elif line.startswith('✦'):
                    current_skill['描述'] = line.replace('✦', '').strip()

        # 添加最后一个技能
        if current_skill and '名称' in current_skill:
            skills.append(current_skill)

        # 将技能列表转为 JSON 字符串
        if skills:
            result['技能列表'] = json.dumps(skills, ensure_ascii=False)

        print(f"✓ 成功解析：{result['编号']} {result['名称']}")
        return result

    except Exception as e:
        print(f"✗ 解析 {pokemon_name} 失败：{e}")
        return result


COLUMNS_ORDER = [
    '编号', '名称', '属性', '种族值总和',
    '生命', '物攻', '魔攻', '物防', '魔防', '速度',
    '特性名称', '特性描述', '技能列表'
]


def init_csv(filename='pokemon_data.csv'):
    """
    初始化 CSV 文件，写入表头
    """
    df = pd.DataFrame(columns=COLUMNS_ORDER)
    df.to_csv(filename, index=False, encoding='utf-8-sig', mode='w')


def append_to_csv(data, filename='pokemon_data.csv'):
    """
    流式追加单条数据到 CSV 文件
    """
    df = pd.DataFrame([data])
    df = df[COLUMNS_ORDER]
    df.to_csv(filename, index=False, encoding='utf-8-sig', mode='a', header=False)


def main():
    """
    主函数
    """
    print("=" * 60)
    print("洛克王国手游精灵数据爬虫")
    print("=" * 60)

    # 1. 获取所有精灵链接
    pokemon_list = get_all_pokemon_links()

    if not pokemon_list:
        print("未找到精灵列表，请检查网络连接或页面结构")
        return

    # 2. 初始化 CSV 文件
    filename = 'pokemon_data.csv'
    init_csv(filename)

    # 3. 逐个抓取精灵详情，流式写入 CSV
    success_count = 0

    for idx, (pokemon_name, url) in enumerate(pokemon_list, 1):
        print(f"\n[{idx}/{len(pokemon_list)}] 正在抓取：{pokemon_name}")

        data = parse_pokemon_detail(url, pokemon_name)

        # 编号为空说明不是有效精灵，跳过不写入
        if not data['编号']:
            print(f"  ⚠ 跳过：未获取到有效编号，可能不是精灵页面")
            continue

        append_to_csv(data, filename)
        success_count += 1

        # 礼貌性延迟，避免请求过快
        time.sleep(0.5)

    # 4. 统计信息
    fail_count = len(pokemon_list) - success_count
    print(f"\n抓取完成！")
    print(f"总计：{len(pokemon_list)} 个链接")
    print(f"成功写入：{success_count} 个")
    print(f"跳过（无效）：{fail_count} 个")
    print(f"数据已保存到 {filename}")


if __name__ == '__main__':
    main()
