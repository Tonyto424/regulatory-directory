#!/usr/bin/env python3
"""
每日全源巡检爬虫 - 从 AJAX/JSON 接口抓取最新法规
适用于 cron 触发

源列表：
  - 网信办 ×5（部门规章/规范性文件/行政法规/政策文件/司法解释）
    接口：/cms/JsonList?channelCode=xxx
  - 中国政府网-最新政策
    接口：ZUIXINZHENGCE.json
"""
import json, re, os, sys, urllib.request, urllib.error, urllib.parse, ssl
from datetime import datetime

HTML_FILE = os.path.join(os.path.dirname(__file__), '..', 'index.html')
META_FILE = os.path.join(os.path.dirname(__file__), '..', '_metadata.json')
NEW_FILE = os.path.join(os.path.dirname(__file__), '..', '_new_items.md')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# ── 网信办：通过 AJAX JSON 接口拉取 ──
CAC_AJAX_URL = 'https://www.cac.gov.cn/cms/JsonList'
CAC_SOURCES = [
    ('网信办-部门规章',  'A09370303', 'bmgz'),
    ('网信办-规范性文件', 'A09370305', 'gfxwj'),
    ('网信办-行政法规',  'A09370302', 'xzfg'),
    ('网信办-政策文件',  'A09370306', 'zcwj'),
    ('网信办-司法解释',  'A09370304', 'sfjs'),
]

# ── 中国政府网：通过 JSON 接口拉取 ──
GOV_JSON_URL = 'https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json'
GOV_SOURCE_NAME = '中国政府网-最新政策'


def fetch_json(url, data=None, referer=''):
    """HTTP POST / GET 请求，返回 JSON 对象"""
    headers = {'User-Agent': UA, 'Content-Type': 'application/x-www-form-urlencoded'}
    if referer:
        headers['Referer'] = referer
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
        return json.loads(resp.read().decode('utf-8'))


def normalize_title(title):
    """标准化法规名称（用于去重比对）"""
    t = title.strip()
    t = re.sub(r'关于印发《', '', t)
    t = re.sub(r'》的通知$', '', t)
    t = re.sub(r'^《|》$', '', t)
    t = re.sub(r'\s+', '', t)
    return t


def is_relevant_title(title):
    """判断标题是否看起来像法规/标准/政策"""
    if len(title) < 4:
        return False
    skip = {'设为首页','加入收藏','首页','搜索','登录','注册','退出','邮箱','无障碍',
            '手机版','电脑版','客户端','小程序','返回顶部','联系我们','网站地图',
            'English','EN','繁体','简','网站声明','隐私政策','关于我们','帮助',
            '全国人大','全国政协','国务院部门','地方政府','驻港澳','驻外'}
    if title.strip() in skip:
        return False
    keywords = ['法','条例','规定','办法','细则','规范','指南','指引','标准','通知',
                '意见','决定','公告','通告','批复','规则','目录','分类','许可','备案',
                '管理','处罚','保护','安全','监管','合规','禁止','限制','审查','评估',
                '认证','标识','编码','分级','分类']
    return any(k in title for k in keywords)


def fetch_cac_source(name, code, subpath, known_set, new_found):
    """拉取网信办一个分类的全部法规"""
    ref = f'https://www.cac.gov.cn/wxzw/zcfg/{subpath}/A{code}index_1.htm'
    payload = urllib.parse.urlencode({
        'channelCode': code, 'perPage': '50', 'pageno': '1',
        'condition': '0', 'fuhao': '=', 'value': ''
    }).encode('utf-8')
    try:
        result = fetch_json(CAC_AJAX_URL, data=payload, referer=ref)
        items = result.get('list', [])
        print(f'  {name}: {len(items)} 条')
        count = 0
        for item in items:
            title = item.get('topic', '').strip()
            if not title or not is_relevant_title(title):
                continue
            pubtime = item.get('pubtime', '')[:10]  # YYYY-MM-DD
            infourl = item.get('infourl', '')
            if infourl.startswith('//'):
                infourl = 'https:' + infourl
            nt = normalize_title(title)
            if nt not in known_set:
                new_found.append({
                    'source': name,
                    'title': nt,
                    'date': pubtime,
                    'url': infourl,
                    'raw_title': title,
                })
                known_set.add(nt)
                count += 1
        return count
    except Exception as e:
        print(f'  {name}: 失败 - {str(e)[:80]}')
        return -1


def fetch_gov_source(known_set, new_found):
    """拉取中国政府网最新政策"""
    try:
        items = fetch_json(GOV_JSON_URL)
        print(f'  {GOV_SOURCE_NAME}: {len(items)} 条')
        count = 0
        for item in items:
            title = item.get('title', '').strip()
            if not title or not is_relevant_title(title):
                continue
            date = item.get('date', '')[:10]
            url = item.get('url', '')
            if url and not url.startswith('http'):
                url = 'https://www.gov.cn' + url
            nt = normalize_title(title)
            if nt not in known_set:
                new_found.append({
                    'source': GOV_SOURCE_NAME,
                    'title': nt,
                    'date': date,
                    'url': url,
                    'raw_title': title,
                })
                known_set.add(nt)
                count += 1
        return count
    except Exception as e:
        print(f'  {GOV_SOURCE_NAME}: 失败 - {str(e)[:80]}')
        return -1


def crawl():
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    # 载入基线
    try:
        with open(META_FILE, 'r', encoding='utf-8') as f:
            meta = json.load(f)
    except:
        meta = {'knownLaws': [], 'knownCases': [], 'lastCrawl': ''}

    known_set = set(meta['knownLaws'])
    new_found = []

    # ── 爬取各源 ──
    for name, code, subpath in CAC_SOURCES:
        fetch_cac_source(name, code, subpath, known_set, new_found)

    fetch_gov_source(known_set, new_found)

    # ── 去重：移除已存在于 HTML 中的法规 ──
    existing = set()
    for m in re.finditer(r'{name:"([^"]+)"', html):
        existing.add(m.group(1))

    truly_new = [n for n in new_found if normalize_title(n['title']) not in existing]

    # ── 输出结果 ──
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n巡检完成: {now_str}')
    print(f'当前已知: {len(known_set)} 条')
    print(f'新增(未去重): {len(new_found)} 条')
    print(f'真正新增: {len(truly_new)} 条')

    for n in truly_new[:15]:
        url_str = f' | {n.get("url","")[:50]}' if n.get('url') else ''
        print(f'  🆕 [{n["source"]}] {n["title"]} ({n["date"]}){url_str}')
    if len(truly_new) > 15:
        print(f'  ... 还有 {len(truly_new)-15} 条')

    # 更新元数据
    meta['knownLaws'] = sorted(known_set)
    meta['lastCrawl'] = now_str
    with open(META_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # ── 如有新增法规，更新 HTML ──
    if truly_new:
        report = f'# 新增法规报告\n\n巡检时间: {now_str}\n\n'
        report += '| 来源 | 法规名称 | 日期 |\n|------|----------|------|\n'
        for n in truly_new:
            report += f'| {n["source"]} | {n["title"]} | {n["date"]} |\n'
        with open(NEW_FILE, 'w', encoding='utf-8') as f:
            f.write(report)

        new_law_names = [n['title'] for n in truly_new]
        html = re.sub(
            r'var _newLaws=\[.*?\];',
            f'var _newLaws={json.dumps(new_law_names, ensure_ascii=False)};',
            html
        )
        with open(HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'\n已更新 _newLaws，标记 {len(truly_new)} 条新增法规')
    else:
        html = re.sub(r'var _newLaws=\[.*?\];', 'var _newLaws=[];', html)
        with open(HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(html)
        print('\n无新增法规')

    return len(truly_new)


if __name__ == '__main__':
    count = crawl()
    sys.exit(0 if count >= 0 else 1)
