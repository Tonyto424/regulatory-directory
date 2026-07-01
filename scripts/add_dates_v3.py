#!/usr/bin/env python3
"""
给 ENF_EVENTS 每条记录加 dt 字段（YYYY-MM-DD），优先从 URL/标题提取具体日期。
"""
import re

with open('/tmp/regulatory-repo/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 定位 ENF_EVENTS 数组
start = html.index('const ENF_EVENTS = [')
end = html.index('];\nconst ENF_RD', start) + 2

entries_raw = html[start:end]

# 更稳健的提取：逐行解析
lines = entries_raw.split('\n')
entries = []
current_lines = []
for line in lines:
    stripped = line.strip()
    if stripped == 'const ENF_EVENTS = [' or stripped == '[':
        continue
    if stripped == '];':
        break
    current_lines.append(stripped)
    if stripped.endswith('},') or stripped.endswith('}'):
        # Join and parse this object
        obj_str = ','.join(current_lines)
        # Extract key-value pairs
        obj = {}
        for m in re.finditer(r'"(y|dt|t|tp|b|r|d|u1|l1)"\s*:\s*"((?:[^"\\]|\\.)*)"', obj_str):
            key = m.group(1)
            val = m.group(2).replace('\\"', '"').replace('\\\\', '\\')
            obj[key] = val
        if obj.get('y') or obj.get('t'):
            entries.append(obj)
        current_lines = []

print(f"Parsed {len(entries)} events")

def extract_dt(y_field, title, url):
    """从 y/title/url 中提取 YYYY-MM-DD"""
    # 格式: 2026.06 → 2026-06-01 (月级)
    # URL 中的具体日期优先
    if url:
        # yyyy-mm-dd
        m = re.search(r'/(\d{4})-(\d{2})-(\d{2})(?:/|$|\.)', url)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        # yyyymmdd (8位连续数字, 不在更长的数字串中)
        m = re.search(r'[^/\d](\d{4})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?:/|[^/\d]|$)', url)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        # yyyy/mm/dd
        m = re.search(r'/(\d{4})/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])(?:/|$)', url)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    
    # 标题中的 "X月X日"
    m = re.search(r'(\d{1,2})月(\d{1,2})[日号]', title)
    if m and '.' in y_field:
        year = y_field.split('.')[0]
        month = m.group(1).zfill(2)
        day = m.group(2).zfill(2)
        if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
            return f"{year}-{month}-{day}"
    
    # 回退：从 y 字段获取月份
    if '.' in y_field:
        parts = y_field.split('.')
        year, month = parts[0], parts[1].zfill(2)
        if 1 <= int(month) <= 12:
            return f"{year}-{month}-01"
    return f"{y_field}-01-01"

# 重建 ENF_EVENTS 数组
new_lines = ['const ENF_EVENTS = [']
for obj in entries:
    dt = extract_dt(obj.get('y', ''), obj.get('t', ''), obj.get('u1', ''))
    
    parts = []
    for key in ['y', 'dt', 't', 'tp', 'b', 'r', 'd']:
        val = obj.get(key, '')
        val_js = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
        parts.append(f'"{key}":"{val_js}"')
    for key in ['u1', 'l1']:
        if key in obj and obj[key]:
            val_js = obj[key].replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
            parts.append(f'"{key}":"{val_js}"')
    
    new_lines.append('  {' + ','.join(parts) + '},')
    print(f"  {obj.get('y','N/A'):>8s} → {dt}  | {obj.get('t','')[:50]}")
new_lines.append('];')

html = html[:start] + '\n'.join(new_lines) + html[end:]

# 替换 renderDaily 中的日期显示
html = html.replace("'📅 '+nr.y+'</div>'", "'📅 '+nr.dt+'</div>'")
html = html.replace("'📅 '+p.y+' · '+p.tp+'</div>'", "'📅 '+p.dt+' · '+p.tp+'</div>'")
html = html.replace("'📅 '+ev.y+' · '+ev.tp+'</div>'", "'📅 '+ev.dt+' · '+ev.tp+'</div>'")
html = html.replace("'📅 '+dp.y+'</div>'", "'📅 '+dp.dt+'</div>'")

with open('/tmp/regulatory-repo/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\n✅ Done! All events now have dt field, renderDaily shows dt.")
