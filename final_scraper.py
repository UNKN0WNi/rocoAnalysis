#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
洛克王国精灵数据爬虫 - 修复版（修正名称+去掉编号）
修复：被动技能（特性）+ 进化链爬取（支持图片+链接格式）+ 种族值总和 + 无技能跳过
"""
import json
import re
import os
import csv
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://wiki.biligame.com/'
}


def get_page(url, retry=3):
    """获取页面内容"""
    for i in range(retry):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.encoding = 'utf-8'
            return resp.text
        except Exception as e:
            print(f"  请求失败，重试 {i + 1}/{retry}: {e}")
            time.sleep(2)
    return None


def extract_links_from_file():
    """从已保存的文件中提取精灵链接"""
    print("正在从已保存内容中提取精灵列表...")
    file_path = 'elf_list.txt'
    if not os.path.exists(file_path):
        print("文件不存在!")
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f"读取到 {len(lines)} 行")
    links = []
    pattern = r'https://wiki\.biligame\.com/rocom/(.+)'
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = re.match(pattern, line)
        if match:
            name_encoded = match.group(1)
            # 修正：从URL解码获取准确名称
            name = unquote(name_encoded)
            links.append({
                'name': name,
                'url': line
            })
    print(f"正则匹配到 {len(links)} 个链接")
    # 去重
    seen = set()
    unique_links = []
    for link in links:
        if link['url'] not in seen:
            seen.add(link['url'])
            unique_links.append(link)
    return unique_links


def extract_skills(tab):
    """从tab中提取技能（保持原逻辑）"""
    skills = []
    skill_boxes = tab.find_all('div', class_='rocom_sprite_skill_box')
    for box in skill_boxes:
        skill = {
            'level': '', 'name': '', 'energy_cost': '',
            'skill_type': '', 'power': '', 'description': ''
        }
        level_div = box.find('div', class_=lambda x: x and 'skill_level' in str(x) if x else False)
        if level_div: skill['level'] = level_div.get_text(strip=True)
        name_div = box.find('div', class_=lambda x: x and 'skillName' in str(x) if x else False)
        if name_div: skill['name'] = name_div.get_text(strip=True)
        damage_div = box.find('div', class_=lambda x: x and 'skillDamage' in str(x) if x else False)
        if damage_div: skill['energy_cost'] = damage_div.get_text(strip=True)
        type_div = box.find('div', class_=lambda x: x and 'skillType' in str(x) if x else False)
        if type_div: skill['skill_type'] = type_div.get_text(strip=True)
        power_div = box.find('div', class_=lambda x: x and 'skill_power' in str(x) if x else False)
        if power_div: skill['power'] = power_div.get_text(strip=True)
        content_div = box.find('div', class_=lambda x: x and 'skillContent' in str(x) if x else False)
        if content_div:
            desc = content_div.get_text(strip=True)
            skill['description'] = desc.lstrip('✦').strip()
        if skill['name']:
            skills.append(skill)
    return skills


def extract_passive_skill(soup):
    """从页面中提取被动技能/特性 - 修复版"""
    passive_skills = []

    # 方法1: 查找"特性"标签区域（这是BWIKI的格式）
    # 特性通常在页面主内容区，以"特性"作为标题
    page_text = soup.get_text()

    # 在页面中查找"特性"相关的文本模式
    # 格式：特性 + 特性名 + 描述

    # 查找所有包含"特性"的h2/h3/h4标题
    headers = soup.find_all(['h2', 'h3', 'h4', 'h5'])
    for header in headers:
        header_text = header.get_text(strip=True)
        if '特性' in header_text:
            # 找到了特性区域，获取其后的内容
            next_elem = header.find_next_sibling()
            if next_elem:
                # 尝试提取特性名称和描述
                content = next_elem.get_text(strip=True)
                # 匹配特性名称模式：图片 + 名称 + 描述
                # 或者直接匹配"名称 + 描述"的模式
                lines = content.split('\n')
                current_name = ''
                current_desc = []

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    # 检查是否是特性名称（通常在两行之间或特定格式中）
                    # BWIKI特性格式: 特性图标 + 特性名称 + 特性描述
                    # 例如: 盲拧 + 回合开始时，技能顺序打乱，4号位的技能能耗-4。

                    # 如果行以特定名称开头或包含特性名
                    if line and not line.startswith('✦') and not line.startswith('特性'):
                        # 这可能是特性名称
                        if len(line) <= 20 and not any(c in line for c in '，。、：；！？'):
                            current_name = line
                        elif current_name:
                            # 这是描述
                            desc = line.lstrip('✦').strip()
                            if desc:
                                passive_skills.append({
                                    'name': current_name,
                                    'description': desc,
                                    'effect': ''
                                })
                                current_name = ''

    # 方法2: 直接在页面文本中搜索特性模式
    if not passive_skills:
        # 搜索类似 "特性\n名称\n描述" 的模式
        pattern = r'特性\s*\n\s*([^\n]{1,15})\s*\n\s*([^\n]{10,200})'
        matches = re.findall(pattern, page_text)
        for name, desc in matches:
            name = name.strip()
            desc = desc.strip()
            if name and len(name) <= 15 and desc:
                passive_skills.append({
                    'name': name,
                    'description': desc,
                    'effect': ''
                })

    # 方法3: 更宽松的匹配
    if not passive_skills:
        # 匹配 "特性名称 + 描述" 的模式
        # 例如：盲拧 回合开始时，技能顺序打乱
        lines = page_text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line and len(line) <= 15 and not line.startswith('✦'):
                # 检查下一行是否是描述
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and ('时' in next_line or '获得' in next_line or '每' in next_line):
                        if len(next_line) > 10:
                            passive_skills.append({
                                'name': line,
                                'description': next_line,
                                'effect': ''
                            })
                            break

    # 去重
    seen = set()
    unique = []
    for ps in passive_skills:
        key = ps['name']
        if key not in seen:
            seen.add(key)
            unique.append(ps)

    return unique


def extract_evolution_chain(soup, current_pokemon_name):
    """从页面中提取进化链信息 - 只返回名字列表
    """
    evolution_chain = []
    seen = set()  # 用于去重

    # 直接定位进化链容器 class="rocom_spirit_evolution_box"
    evolution_box = soup.find('div', class_='rocom_spirit_evolution_box')
    if not evolution_box:
        evolve_p = soup.find('p', class_=lambda x: x and 'evolve_text' in str(x) if x else False)
        if evolve_p:
            evolution_box = evolve_p.find_parent('div', class_=lambda x: x and 'spirit_evolution' in str(x) if x else False)

    if not evolution_box:
        return evolution_chain

    # 查找所有精灵链接（排除导航链接）
    all_links = evolution_box.find_all('a', href=lambda x: x and '/rocom/' in x)

    for link in all_links:
        href = link.get('href', '')

        # 过滤非精灵链接
        skip_keywords = ['Special:', '文件:', 'File:', 'index.php', 'WP:', 'wp',
                        '精灵图鉴', '道具图鉴', '技能图鉴', '首页', '攻略', '任务',
                        '蛋组', '异色', '孵蛋', '阵容', '伤害', '克制', '性格',
                        '精灵筛选', '道具筛选', '技能筛选', '精灵蛋', '精灵果实',
                        '家具', '服装', '地区', '副本', '邮件', '地图']
        if any(kw in href for kw in skip_keywords):
            continue

        # 从href中提取精灵名称
        name_match = re.search(r'/rocom/([^/\?#&]+)', href)
        if not name_match:
            continue

        name_encoded = name_match.group(1)
        name = unquote(name_encoded)

        # 从title属性获取名称（更准确）
        title = link.get('title', '')
        if title and len(title) <= 10:
            name = title

        # 跳过空名称或太长的名称
        if not name or len(name) > 15:
            continue

        if name not in seen:
            seen.add(name)
            evolution_chain.append(name)

    # 如果方法1失败，使用正则从进化链容器文本提取
    if not evolution_chain:
        seen = set()  # 重置seen用于备用方法
        box_text = evolution_box.get_text()
        href_pattern = r'/rocom/([^\s\)"\']+)'
        href_matches = re.findall(href_pattern, box_text)

        for href_match in href_matches:
            if any(kw in href_match for kw in ['Special', '文件', 'File', 'index.php', '精灵图鉴', '首页']):
                continue
            name = unquote(href_match)
            if not name or len(name) > 15:
                continue
            if name not in seen:
                seen.add(name)
                evolution_chain.append(name)

    return evolution_chain


def parse_pokemon_detail(html, fallback_name=''):
    """解析单个精灵页面 - 修复版：特性 + 进化链"""
    soup = BeautifulSoup(html, 'html.parser')
    pokemon = {
        'name': '',
        'attributes': [],
        'base_stats': {},
        'spirit_skills': [],
        'skill_stones': [],
        'passive_skills': [],  # 被动技能/特性
        'evolution_chain': []  # 进化链
    }

    # 名称提取逻辑
    title = soup.find('h1', id='firstHeading')
    if title:
        title_text = title.get_text(strip=True)
        # 清理常见干扰前缀/后缀
        title_text = re.sub(r'^NO\.\d+\s*', '', title_text)  # 移除 "NO.123 "
        title_text = re.sub(r'\s*\(.*?\)', '', title_text)  # 移除 "（洛克王国）"
        title_text = re.sub(r'\s*-\s*.*$', '', title_text)  # 移除 " - 百科"
        if title_text and len(title_text) <= 10:
            pokemon['name'] = title_text.strip()

    # 备用：如果标题提取失败，使用URL解码的名称
    if not pokemon['name'] and fallback_name:
        pokemon['name'] = fallback_name

    current_name = pokemon['name'] or fallback_name

    # 提取属性
    attr_container = soup.find('div', class_='rocom_sprite_grament_attributes')
    if attr_container:
        for img in attr_container.find_all('img'):
            alt = img.get('alt', '')
            match = re.search(r'属性\s+([^\s\.]+)\.png$', alt)
            if match:
                attr_name = match.group(1)
                valid_attrs = {"草", "火", "水", "萌", "武", "毒", "土", "冰", "翼", "光", "暗", "电", "石", "龙",
                               "恶魔", "机械", "幽灵", "普通", "幻"}
                if attr_name in valid_attrs and attr_name not in pokemon['attributes']:
                    pokemon['attributes'].append(attr_name)

    # 兜底：遍历所有图片
    if not pokemon['attributes']:
        for img in soup.find_all('img'):
            alt = img.get('alt', '')
            match = re.search(r'属性\s+([^\s\.]+)\.png$', alt)
            if match:
                attr_name = match.group(1)
                valid_attrs = {"草", "火", "水", "萌", "武", "毒", "土", "冰", "翼", "光", "暗", "电", "石", "龙",
                               "恶魔", "机械", "幽灵", "普通", "幻"}
                if attr_name in valid_attrs and attr_name not in pokemon['attributes']:
                    pokemon['attributes'].append(attr_name)
                    if len(pokemon['attributes']) >= 2:
                        break

    # 提取种族值
    STAT_MAPPING = {
        '生命': 'HP', 'HP': 'HP', '物攻': '物攻', '攻击': '物攻',
        '魔攻': '魔攻', '特攻': '魔攻', '物防': '物防', '防御': '物防',
        '魔防': '魔防', '特防': '魔防', '速度': '速度', '速': '速度'
    }
    pokemon['base_stats'] = {k: '' for k in ['HP', '物攻', '魔攻', '物防', '魔防', '速度']}

    qual_container = soup.find('div', class_='rocom_sprite_info_qualification')
    if qual_container:
        for li in qual_container.find_all('li'):
            name_p = li.find('p', class_='rocom_sprite_info_qualification_name')
            if not name_p:
                continue
            stat_name = name_p.get_text(strip=True)
            std_key = STAT_MAPPING.get(stat_name)
            if not std_key or pokemon['base_stats'][std_key]:
                continue
            value_p = li.find('p', class_='rocom_sprite_info_qualification_value')
            if value_p:
                value_text = value_p.get_text(strip=True)
                num_match = re.search(r'(\d+)', value_text)
                if num_match:
                    pokemon['base_stats'][std_key] = int(num_match.group(1))

    # 提取技能（保持原逻辑）
    tabbertabs = soup.find_all('div', class_='tabbertab')
    for tab in tabbertabs:
        tab_title = tab.get('title', '')
        if '精灵技能' in tab_title:
            pokemon['spirit_skills'] = extract_skills(tab)
        if '可学技能石' in tab_title or '可学习' in tab_title:
            pokemon['skill_stones'] = extract_skills(tab)

    # 提取被动技能/特性
    pokemon['passive_skills'] = extract_passive_skill(soup)

    # 提取进化链
    pokemon['evolution_chain'] = extract_evolution_chain(soup, current_name)

    # 计算种族值总和
    stats = pokemon['base_stats']
    stat_sum = sum(v for v in stats.values() if isinstance(v, (int, float)) and v > 0)
    pokemon['total_stats'] = stat_sum

    return pokemon


def main():
    print("=" * 60)
    print("洛克王国精灵数据批量爬虫")
    print("=" * 60)

    print("\n[步骤1] 提取精灵列表...")
    pokemon_list = extract_links_from_file()
    print(f"找到 {len(pokemon_list)} 个精灵")
    if not pokemon_list:
        print("提取列表失败！")
        return

    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    with open(f'{output_dir}/pokemon_list.json', 'w', encoding='utf-8') as f:
        json.dump(pokemon_list, f, ensure_ascii=False, indent=2)
    print(f"列表已保存到 {output_dir}/pokemon_list.json")

    print("\n[步骤2] 开始爬取精灵详情...")
    all_pokemon = []
    skipped_count = 0
    for i, pokemon_info in enumerate(pokemon_list):
        print(f"  正在爬取 {i + 1}/{len(pokemon_list)}: {pokemon_info['name']}...")
        html = get_page(pokemon_info['url'])
        if html:
            pokemon = parse_pokemon_detail(html, fallback_name=pokemon_info['name'])
            pokemon['url'] = pokemon_info['url']

            # 功能1: 如果技能为空则跳过本精灵
            has_spirit_skills = bool(pokemon.get('spirit_skills'))
            has_skill_stones = bool(pokemon.get('skill_stones'))

            if not has_spirit_skills and not has_skill_stones:
                print(f"    [跳过] 精灵 '{pokemon_info['name']}' 无技能数据")
                skipped_count += 1
                continue

            all_pokemon.append(pokemon)
        else:
            all_pokemon.append({
                'name': pokemon_info['name'],
                'url': pokemon_info['url'],
                'error': '获取页面失败'
            })
        time.sleep(2)

    print(f"\n  已跳过 {skipped_count} 个无技能的精灵")

    print("\n[步骤3] 保存数据...")
    json_path = 'output/all_pokemon.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_pokemon, f, ensure_ascii=False, indent=2)
    print(f"JSON已保存: {json_path}")

    # CSV表头：新增种族值总和列
    csv_path = 'output/all_pokemon.csv'
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(
            ['名称', '属性', 'HP', '物攻', '魔攻', '物防', '魔防', '速度', '种族值总和',
             '精灵技能数', '可学技能石数', '被动技能数', '进化链', 'URL'])
        for p in all_pokemon:
            attrs = ','.join(p.get('attributes', []))
            stats = p.get('base_stats', {})

            # 格式化进化链（现在直接是名字列表）
            evo_chain = p.get('evolution_chain', [])
            evo_str = ' → '.join(evo_chain) if evo_chain else ''

            writer.writerow([
                p.get('name', ''),
                attrs,
                stats.get('HP', ''),
                stats.get('物攻', ''),
                stats.get('魔攻', ''),
                stats.get('物防', ''),
                stats.get('魔防', ''),
                stats.get('速度', ''),
                p.get('total_stats', ''),  # 功能2: 种族值总和
                len(p.get('spirit_skills', [])),
                len(p.get('skill_stones', [])),
                len(p.get('passive_skills', [])),
                evo_str,
                p.get('url', '')
            ])
    print(f"CSV已保存: {csv_path}")

    print("\n" + "=" * 60)
    print("爬取统计:")
    print("=" * 60)
    success = [p for p in all_pokemon if 'error' not in p]
    with_skills = [p for p in success if p.get('spirit_skills')]
    with_stones = [p for p in success if p.get('skill_stones')]
    with_passive = [p for p in success if p.get('passive_skills')]
    with_evo = [p for p in success if p.get('evolution_chain')]
    print(f"成功爬取: {len(success)}/{len(all_pokemon)} 个")
    print(f"有精灵技能: {len(with_skills)} 个")
    print(f"有可学技能石: {len(with_stones)} 个")
    print(f"有被动技能: {len(with_passive)} 个")
    print(f"有进化链: {len(with_evo)} 个")

    print("\n" + "=" * 60)
    print("数据预览:")
    print("=" * 60)
    for p in success[:5]:
        print(f"\n【{p['name']}】")
        print(f"  属性: {','.join(p.get('attributes', []))}")
        stats = p.get('base_stats', {})
        if any(stats.values()):
            total = p.get('total_stats', '')
            print(
                f"  种族值: HP{stats.get('HP', '')} 物攻{stats.get('物攻', '')} 魔攻{stats.get('魔攻', '')} 物防{stats.get('物防', '')} 魔防{stats.get('魔防', '')} 速度{stats.get('速度', '')} (总和: {total})")
        print(f"  精灵技能: {len(p.get('spirit_skills', []))} 个")
        print(f"  可学技能石: {len(p.get('skill_stones', []))} 个")
        print(f"  被动技能: {len(p.get('passive_skills', []))} 个")

        # 显示被动技能详情
        if p.get('passive_skills'):
            for ps in p['passive_skills'][:2]:
                print(f"    └ 特性: {ps.get('name', '未知')} - {ps.get('description', '')[:50]}")

        # 显示进化链（现在直接是名字列表）
        evo_chain = p.get('evolution_chain', [])
        if evo_chain:
            print(f"  进化链: {' → '.join(evo_chain)}")

    print("\n" + "=" * 60)
    print("爬取完成!")


if __name__ == "__main__":
    main()