#!/usr/bin/env python3
"""
给 ENF_EVENTS 每条记录加 dt 字段（具体到日）。
同时修改 renderDaily 中显示 y 的地方改成 dt。
"""
import re

with open('/tmp/regulatory-repo/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. 定位 ENF_EVENTS
start = html.index('const ENF_EVENTS = [')
end = html.index('];\nconst ENF_RD', start) + 2

# 2. 逐条提取 { ... }
entries_raw = html[start:end]
entries_list = []

# 正则：每个 {key:"val",key2:"val2",...} 
pattern = re.compile(r'{([^}]+)}')
for m in pattern.finditer(entries_raw):
    block = m.group(1)
    # 解析键值对
    obj = {}
    # 匹配 key:"value" 对，value可能含转义引号
    for kv in re.finditer(r'("(?:[^"\\]|\\.)*")\s*:\s*("(?:[^"\\]|\\.)*")', block):
        key = re.sub(r'"', '', kv.group(1))
        val = re.sub(r'"', '', kv.group(2))
        val = val.replace('\\"', '"')
        obj[key] = val
    if obj.get('y') or obj.get('t'):
        entries_list.append(obj)

print(f"Parsed {len(entries_list)} events")

def extract_dt(y_field, title, url):
    """从 y/title/url 中提取 YYYY-MM-DD"""
    # 1. 从 URL 提取 (如 .../2026-06-24/... 或 .../20260624/... 或 .../2026-06/24/...)
    if url:
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})', url)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        m = re.search(r'/(\d{4})(\d{2})(\d{2})\b', url)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        m = re.search(r'/20(\d{2})/(\d{2})/(\d{2})/', url)
        if m:
            return f"20{m.group(1)}-{m.group(2)}-{m.group(3)}"
    
    # 2. 从标题提取 "X月X日"
    m = re.search(r'(\d{1,2})月(\d{1,2})[日号]', title)
    if m and '.' in y_field:
        year = y_field.split('.')[0]
        month = m.group(1).zfill(2)
        day = m.group(2).zfill(2)
        return f"{year}-{month}-{day}"
    
    # 3. 回退到 y 字段
    if '.' in y_field:
        parts = y_field.split('.')
        year, month = parts[0], parts[1].zfill(2)
        return f"{year}-{month}-01"
    return f"{y_field}-01-01"

# 3. 重建 ENF_EVENTS
new_lines = ['const ENF_EVENTS = [']
for obj in entries_list:
    dt = extract_dt(obj.get('y', ''), obj.get('t', ''), obj.get('u1', ''))
    # 加入 dt 字段（排在 y 后面）
    parts = []
    for key in ['y', 'dt', 't', 'tp', 'b', 'r', 'd']:
        val = obj.get(key, '')
        val_js = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
        parts.append(f'"{key}":"{val_js}"')
    for key in ['u1', 'l1']:
        if key in obj and obj[key]:
            val_js = obj[key].replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
            parts.append(f'"{key}":"{val_js}"')
    
    line = '  {' + ','.join(parts) + '},'
    new_lines.append(line)
new_lines.append('];')
new_events_text = '\n'.join(new_lines)

# 4. 替换 HTML
html = html[:start] + new_events_text + html[end:]

# 5. 修改 renderDaily 中所有显示 y 的地方改成 dt
# 在 renderDaily 中，日期显示用 📅 行，格式为 📅 ev.y, 📅 nr.y, 📅 p.y, 📅 dp.y
# 把 .y 改成 .dt 显示
# 但对于分类逻辑（按 tp 分组）依然用 y 排序，不影响

# 找出所有显示日期的行
# 新法规: '📅 '+nr.y+'</div>'
html = html.replace("'📅 '+nr.y+'</div>'", "'📅 '+nr.dt+'</div>'")
# 执法处罚: '📅 '+p.y+' · '+p.tp+'</div>'
html = html.replace("'📅 '+p.y+' · '+p.tp+'</div>'", "'📅 '+p.dt+' · '+p.tp+'</div>'")
# 监管通报: '📅 '+ev.y+' · '+ev.tp+'</div>'
html = html.replace("'📅 '+ev.y+' · '+ev.tp+'</div>'", "'📅 '+ev.dt+' · '+ev.tp+'</div>'")
# 监管数据: '📅 '+dp.y+'</div>'
html = html.replace("'📅 '+dp.y+'</div>'", "'📅 '+dp.dt+'</div>'")

# 6. 写入
with open('/tmp/regulatory-repo/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done! dt fields added and renderDaily updated to show dt.")
print(f"Total events: {len(entries_list)}")

# 打印各条 dt 值确认
for obj in entries_list:
    dt = extract_dt(obj.get('y', ''), obj.get('t', ''), obj.get('u1', ''))
    print(f"  {obj.get('y','N/A'):>8s} → {dt}  | {obj.get('t','')[:50]}")
