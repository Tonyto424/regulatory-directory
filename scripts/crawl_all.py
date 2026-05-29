#!/usr/bin/env python3
"""
每日全源巡检爬虫 - 从所有参考源抓取最新法规
适用于 cron 触发
"""
import json, re, os, sys, urllib.request, urllib.error, ssl, html as html_mod
from datetime import datetime
from difflib import SequenceMatcher

HTML_FILE = os.path.join(os.path.dirname(__file__), '..', 'index.html')
META_FILE = os.path.join(os.path.dirname(__file__), '..', '_metadata.json')
NEW_FILE = os.path.join(os.path.dirname(__file__), '..', '_new_items.md')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read()
            try:
                text = data.decode('utf-8')
            except:
                text = data.decode('gbk', errors='replace')
            return text
    except Exception as e:
        raise Exception(str(e)[:80])

def extract_links(html, base_url):
    """提取 HTML 中的所有链接和标题"""
    results = []
    # <a href="...">title</a>
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>', html, re.I):
        href = m.group(1).strip()
        title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if not title or not href:
            continue
        if href.startswith('#'):
            continue
        if href.startswith('//'):
            href = 'https:' + href
        elif href.startswith('/'):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            href = f'{parsed.scheme}://{parsed.netloc}{href}'
        if not href.startswith('http'):
            continue
        results.append({'title': title, 'url': href})
    return results

def is_relevant_title(title):
    """判断标题是否看起来像法规/标准/政策"""
    if len(title) < 4 or len(title) > 80:
        return False
    skip = {'设为首页','加入收藏','首页','搜索','登录','注册','退出','邮箱','无障碍',
            '手机版','电脑版','客户端','小程序','返回顶部','联系我们','网站地图',
            'English','EN','繁体','简','网站声明','隐私政策','关于我们','帮助',
            '全国人大','全国政协','国务院部门','地方政府','驻港澳','驻外'}
    if title.strip() in skip:
        return False
    # 包含法规关键词
    keywords = ['法','条例','规定','办法','细则','规范','指南','指引','标准','通知',
                '意见','决定','公告','通告','批复','规则','目录','分类','许可','备案',
                '管理','处罚','保护','安全','监管','合规','禁止','限制','审查','评估',
                '认证','标识','编码','分级','分类']
    return any(k in title for k in keywords)

def normalize_title(title):
    """标准化法规名称"""
    t = title.strip()
    t = re.sub(r'关于印发《', '', t)
    t = re.sub(r'》的通知$', '', t)
    t = re.sub(r'^《|》$', '', t)
    t = re.sub(r'\s+', '', t)
    return t

# ===== 主爬虫逻辑 =====
def crawl():
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    # 从页面提取所有参考源 URL
    source_urls = set()
    for m in re.finditer(r'u:"([^"]+)"', html):
        url = m.group(1)
        if url.startswith('http'):
            source_urls.add(url)

    # 也提取 getSrc 映射中的法规 URL
    law_urls = set()
    src_match = re.search(r'function getSrc\(s\)\{([\s\S]*?)\}', html)
    if src_match:
        for m in re.finditer(r"'([^']+)'", src_match.group(1)):
            u = m.group(1)
            if u.startswith('http'):
                law_urls.add(u)

    print(f'参考源: {len(source_urls)} 个, 法规链接: {len(law_urls)} 个')

    # 载入基线
    try:
        with open(META_FILE, 'r', encoding='utf-8') as f:
            meta = json.load(f)
    except:
        meta = {'knownLaws': [], 'knownCases': [], 'lastCrawl': ''}
    
    known_set = set(meta['knownLaws'])
    new_found = []

    # 爬取各源
    sources_to_crawl = [
        # CAC 官方分类页 - 最重要的源
        ('网信办-部门规章', 'https://www.cac.gov.cn/wxzw/zcfg/bmgz/A09370303index_1.htm'),
        ('网信办-规范性文件', 'https://www.cac.gov.cn/wxzw/zcfg/gfxwj/A09370305index_1.htm'),
        ('网信办-行政法规', 'https://www.cac.gov.cn/wxzw/zcfg/xzfg/A09370302index_1.htm'),
        ('网信办-政策文件', 'https://www.cac.gov.cn/wxzw/zcfg/zcwj/A09370306index_1.htm'),
        ('网信办-司法解释', 'https://www.cac.gov.cn/wxzw/zcfg/sfjs/A09370304index_1.htm'),
        # 更多源
        ('中国政府网-最新政策', 'https://www.gov.cn/zhengce/zuixin/'),
    ]

    for src_name, src_url in sources_to_crawl:
        try:
            content = fetch(src_url)
            links = extract_links(content, src_url)
            # 提取 <li> 列表
            items = []
            for li in re.finditer(r'<li[^>]*>([\s\S]*?)</li>', content):
                li_text = li.group(1)
                a = re.search(r'<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>', li_text)
                if a:
                    t = re.sub(r'<[^>]+>', '', a.group(2)).strip()
                    d = re.search(r'(\d{4}-\d{2}-\d{2})', li_text)
                    date = d.group(1) if d else ''
                    if t and len(t) > 4:
                        items.append({'title': t, 'date': date})
            
            print(f'  {src_name}: {len(items)} 条')
            
            for item in items:
                nt = normalize_title(item['title'])
                if not nt or len(nt) < 4:
                    continue
                if not is_relevant_title(nt):
                    continue
                if nt not in known_set:
                    new_found.append({'source': src_name, 'title': nt, 'date': item.get('date','')})
                    known_set.add(nt)
        except Exception as e:
            print(f'  {src_name}: 失败 - {e}')

    # ===== 去重：移除已存在的法规 =====
    # 从 HTML 中提取当前所有法规名
    existing = set()
    for m in re.finditer(r'{name:"([^"]+)"', html):
        existing.add(m.group(1))
    
    truly_new = [n for n in new_found if normalize_title(n['title']) not in existing]

    # ===== 输出结果 =====
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n巡检完成: {now_str}')
    print(f'当前已知: {len(known_set)} 条')
    print(f'新增(未去重): {len(new_found)} 条')
    print(f'真正新增: {len(truly_new)} 条')

    for n in truly_new[:15]:
        print(f'  🆕 [{n["source"]}] {n["title"]} ({n["date"]})')
    if len(truly_new) > 15:
        print(f'  ... 还有 {len(truly_new)-15} 条')

    # ===== 更新元数据 =====
    meta['knownLaws'] = sorted(known_set)
    meta['lastCrawl'] = now_str
    with open(META_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # ===== 如果发现新法规，更新 HTML =====
    if truly_new:
        # 写报告
        report = f'# 新增法规报告\n\n巡检时间: {now_str}\n\n'
        report += '| 来源 | 法规名称 | 日期 |\n|------|----------|------|\n'
        for n in truly_new:
            report += f'| {n["source"]} | {n["title"]} | {n["date"]} |\n'
        with open(NEW_FILE, 'w', encoding='utf-8') as f:
            f.write(report)

        # 更新 HTML 中的 _newLaws 数组
        new_law_names = [n['title'] for n in truly_new]
        new_law_js = f'var _newLaws={json.dumps(new_law_names, ensure_ascii=False)};\n'
        new_law_js += f'var _lastCrawl="{now_str}";\n'
        
        # 替换 _newLaws 声明
        html = re.sub(
            r'var _newLaws=\[.*?\];',
            f'var _newLaws={json.dumps(new_law_names, ensure_ascii=False)};',
            html
        )

        with open(HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f'\n已更新 _newLaws，标记 {len(truly_new)} 条新增法规')
        
        # 标记红点逻辑在 JS 端运行（页面加载时根据 _newLaws 判断）
    else:
        # 没有新增，清空 _newLaws
        html = re.sub(
            r'var _newLaws=\[.*?\];',
            'var _newLaws=[];',
            html
        )
        with open(HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(html)
        print('\n无新增法规')

    return len(truly_new)

if __name__ == '__main__':
    count = crawl()
    sys.exit(0 if count >= 0 else 1)
