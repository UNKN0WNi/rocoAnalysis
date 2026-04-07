# -*- coding: utf-8 -*-
"""
洛克王国精灵详情页抓取脚本
功能: 抓取精灵的属性、种族值、技能

抓取说明:
- 属性、种族值: 通过 MediaWiki API 获取 (稳定)
- 技能: 需要通过浏览器开发者工具分析实际 API 地址
"""
import requests
from bs4 import BeautifulSoup
import json
import os

# ============== 配置 ==============
SPRITE_NAME = "不咕钟"  # 要抓取的精灵名称
# ============== 配置 ==============

def fetch_wikitext(sprite_name):
    """通过 MediaWiki API 获取 wikitext"""
    url = 'https://wiki.biligame.com/rocom/api.php'
    params = {
        'action': 'parse',
        'page': sprite_name,
        'prop': 'wikitext',
        'format': 'json',
        'formatversion': '2'
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, params=params, headers=headers, timeout=15)
    if response.status_code == 200:
        data = json.loads(response.text)
        return data.get('parse', {}).get('wikitext', '')
    return ''

def parse_wikitext(wikitext):
    """解析 wikitext 中的键值对"""
    result = {}
    for line in wikitext.split('\n'):
        line = line.strip()
        if '|' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                key = parts[0].strip().lstrip('|')
                value = parts[1].strip()
                result[key] = value
    return result

def fetch_with_selenium(sprite_name):
    """
    使用 Selenium 获取渲染后的页面
    注意: 技能数据通过外部 API 加载，此方法可能无法获取完整技能列表
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        import time
    except ImportError:
        print("  Selenium 未安装")
        return ''

    print("  正在使用 Selenium 渲染页面...")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    try:
        os.environ['WDM_SSL_VERIFY'] = '0'
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        url = f"https://wiki.biligame.com/rocom/{sprite_name}"
        driver.get(url)

        # 等待页面基本加载
        time.sleep(5)

        # 获取页面源码
        html_content = driver.page_source
        driver.quit()

        return html_content
    except Exception as e:
        print(f"  Selenium 错误: {e}")
        return ''

def parse_skills(html_content):
    """从渲染后的 HTML 中解析技能"""
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    skills = []

    # 查找所有技能区域
    skill_boxes = soup.find_all('div', class_='rocom_sprite_skill_skillBox')
    for box in skill_boxes:
        # 查找技能链接
        links = box.find_all('a')
        for link in links:
            title = link.get('title', '')
            text = link.get_text(strip=True)
            if title and len(title) > 1:
                if title not in skills:
                    skills.append(title)
            elif text and 1 < len(text) < 30:
                if text not in skills:
                    skills.append(text)

    return skills

def main():
    print("=" * 50)
    print("洛克王国精灵数据抓取")
    print("=" * 50)
    print(f"精灵名称: {SPRITE_NAME}")
    print()

    # 1. 从 MediaWiki API 获取数据
    print("[1] 通过 MediaWiki API 获取属性和种族值...")
    wikitext = fetch_wikitext(SPRITE_NAME)
    wiki_data = parse_wikitext(wikitext)

    # 2. 可选: 使用 Selenium 尝试获取技能
    print("[2] 尝试通过 Selenium 获取技能数据...")
    html_content = fetch_with_selenium(SPRITE_NAME)
    if html_content:
        with open("detail.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("  HTML 已保存到 detail.html")

        skills = parse_skills(html_content)
        if skills:
            print(f"  找到 {len(skills)} 个技能")
        else:
            print("  未找到技能 (技能通过外部 API 加载)")
    else:
        skills = []

    # 3. 输出结果
    print()
    print("=" * 50)
    print("抓取结果:")
    print("=" * 50)

    # 属性
    attributes = []
    if wiki_data.get('主属性'):
        attributes.append(wiki_data['主属性'])
    if wiki_data.get('2属性'):
        attributes.append(wiki_data['2属性'])
    print(f"属性: {', '.join(attributes) if attributes else '未找到'}")

    # 种族值
    print("种族值 (满级种族值):")
    stat_keys = ['生命', '物攻', '魔攻', '物防', '魔防', '速度']
    for stat in stat_keys:
        value = wiki_data.get(stat, '')
        if value:
            print(f"  {stat}: {value}")

    # 技能
    print(f"技能: {len(skills)} 个")
    if skills:
        for i, skill in enumerate(skills[:10], 1):
            print(f"  {i}. {skill}")
        if len(skills) > 10:
            print(f"  ... 还有 {len(skills) - 10} 个")
    else:
        print("  (技能通过外部 API 动态加载，请使用浏览器 F12 分析实际 API)")

if __name__ == "__main__":
    main()