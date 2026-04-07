import requests
from bs4 import BeautifulSoup

# 目标 URL
url = "https://wiki.biligame.com/rocom/不咕钟"

# 请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

print(f"正在请求: {url}")
try:
    # 发送请求
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = 'utf-8'

    print(f"状态码: {response.status_code}")
    print(f"内容长度: {len(response.text)}")

    # 打印前 1000 个字符
    print("\n--- 网页源代码预览 (前 1000 字符) ---")
    print(response.text[:1000])
    print("\n--- 结束 ---")

    # 尝试用 BeautifulSoup 解析
    soup = BeautifulSoup(response.text, 'html.parser')

    # 看看能不能找到表格
    tables = soup.find_all('table')
    print(f"\n解析到的表格数量: {len(tables)}")

    # 如果表格是 0，看看 body 里有什么
    if len(tables) == 0:
        body = soup.find('body')
        print(f"Body 内容预览: {body.text[:500] if body else '无 Body 标签'}")

except Exception as e:
    print(f"错误: {e}")