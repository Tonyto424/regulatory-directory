#!/usr/bin/env python3
"""给 ENF_EVENTS 每条加 dt 字段（YYYY-MM-DD），并修改 renderDaily 显示 dt。"""
import re

with open('/tmp/regulatory-repo/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 定位 ENF_EVENTS 数组
arr_start = html.index('const ENF_EVENTS = [')
arr_end = html.index('];\nconst ENF_RD', arr_start) + 2
arr_text = html[arr_start:arr_end]

# 逐行提取每个事件对象
lines = arr_text.split('\n')
entries = []
curr_lines = []
for line in lines:
    s = line.strip()
    if 'const ENF_EVENTS' in s or s == '[':
        continue
    if s == '];':
        break
    curr_lines.append(s)
    if s.endswith('},') or s == '}':
        raw = ','.join(curr_lines)
        # 提取 key-value pairs
        obj = dict(re.findall(r'"(\w+)"\s*:\s*"((?:[^"\\]|\\.)*)"', raw))
        if obj.get('y') or obj.get('t'):
            entries.append(obj)
        curr_lines = []

print(f"Parsed {len(entries)} events")

def extract_dt(y, t, u1, l1):
    """从 y/title/url 中提取 YYYY-MM-DD"""
    for url in (u1, l1):
        if not url: continue
        # yyyy-mm-dd
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})(?:/|$|\\|\.)', url)
        if m:
            yy, mm, dd = m.group(1), m.group(2), m.group(3)
            if 2000 <= int(yy) <= 2100 and 1 <= int(mm) <= 12 and 1 <= int(dd) <= 31:
                return f"{yy}-{mm}-{dd}"
        # yyyy/mm/dd
        m = re.search(r'(\d{4})/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])(?:/|$)', url)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # 标题中 "X月X日"
    m = re.search(r'(\d{1,2})月(\d{1,2})[日号]', t)
    if m and '.' in y:
        yr = y.split('.')[0]
        mo = m.group(1).zfill(2)
        dd = m.group(2).zfill(2)
        if 1 <= int(mo) <= 12 and 1 <= int(dd) <= 31:
            return f"{yr}-{mo}-{dd}"
    # 回退到 y 字段的月份
    if '.' in y:
        parts = y.split('.')
        yr, mo = parts[0], parts[1].zfill(2)
        if len(yr) == 4 and 1 <= int(mo) <= 12:
            return f"{yr}-{mo}-01"
    if len(y) == 4 and y.isdigit():
        return f"{y}-01-01"
    return f"{y}-01-01"

def esc(val):
    """转义 JS 字符串中的特殊字符"""
    return val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')

# 重建 ENF_EVENTS 数组
new_lines = ['const ENF_EVENTS = [']
for obj in entries:
    dt = extract_dt(obj.get('y',''), obj.get('t',''), obj.get('u1',''), obj.get('l1',''))
    parts = [f'"y":"{esc(obj.get("y",""))}"', f'"dt":"{dt}"']
    for key in ['t', 'tp', 'b', 'r', 'd']:
        parts.append(f'"{key}":"{esc(obj.get(key,""))}"')
    for key in ['u1', 'l1']:
        val = obj.get(key, '')
        if val:
            parts.append(f'"{key}":"{esc(val)}"')
    new_lines.append('  {' + ','.join(parts) + '},')
    print(f"  {obj.get('y','N/A'):>8s} -> {dt}  | {obj.get('t','')[:50]}")
new_lines.append('];')

html = html[:arr_start] + '\n'.join(new_lines) + html[arr_end:]

# 修改 renderDaily 中的日期显示
html = html.replace("'+nr.y+'", "'+nr.dt+'")
html = html.replace("'+p.y+'", "'+p.dt+'")
html = html.replace("'+ev.y+'", "'+ev.dt+'")
html = html.replace("'+dp.y+'", "'+dp.dt+'")

with open('/tmp/regulatory-repo/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\nDone! dt fields added and renderDaily updated.")
