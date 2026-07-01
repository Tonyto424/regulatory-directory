#!/usr/bin/env python3
"""
给 ENF_EVENTS 中每条加入 dt (YYYY-MM-DD) 字段，从 URL/标题 中提取具体日期
"""
import re, json

with open('/tmp/regulatory-repo/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Locate ENF_EVENTS array
start = html.index('const ENF_EVENTS = [')
end = html.index('];\nconst ENF_RD', start) + 2
arr_text = html[start:end]

# Extract each object
# Simple approach: find individual {...} entries
entries_text = arr_text[arr_text.index('['):arr_text.rindex(']')+1]
# Parse as JSON - need to handle JS line
# Build a proper JS-like string
lines = arr_text.split('\n')
objects_text = []
current = []
for line in lines:
    if line.strip().startswith('const ') or line.strip().startswith('const '):
        continue
    current.append(line)
    if line.strip().endswith('},') or line.strip().endswith('}'):
        pass

# Better approach: parse manually
# Find all {...} between [ and ]
import json as json_mod

# Let's extract the JSON-like string
start_bracket = arr_text.index('[')
end_bracket = arr_text.rindex(']')
json_str = arr_text[start_bracket:end_bracket+1]

# Fix trailing commas in JSON
json_str = re.sub(r',\s*}', '}', json_str)
json_str = re.sub(r',\s*]', ']', json_str)

# Remove JS comments if any
json_str = re.sub(r'//.*?\n', '\n', json_str)

# Try to parse
try:
    events = json_mod.loads(json_str)
    print(f"Parsed {len(events)} events")
except json_mod.JSONDecodeError as e:
    print(f"JSON error: {e}")
    # Try to fix common issues
    # Sometimes the objects have trailing comma before closing
    json_str = re.sub(r',\s*]', ']', json_str)
    try:
        events = json_mod.loads(json_str)
        print(f"Parsed {len(events)} events (after fix)")
    except json_mod.JSONDecodeError as e2:
        print(f"Still fails: {e2}")
        exit(1)

def extract_date_from_url(url):
    """Extract date from URL patterns"""
    if not url:
        return None
    patterns = [
        r'/(\d{4})-(\d{2})/(\d{2})',    # 2026-06/24
        r'(\d{4})-(\d{2})-(\d{2})',      # 2026-06-24
        r'/(\d{4})(\d{2})(\d{2})',       # 20260603
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            g = m.groups()
            if len(g) == 3:
                return f"{g[0]}-{g[1]}-{g[2]}"
    return None

def extract_date_from_title(title, y):
    """Extract date from title"""
    # "截至4月30日" patterns
    m = re.search(r'(\d{1,2})月(\d{1,2})[日号]', title)
    if m:
        month_part = y.split('.')[1] if '.' in y else '01'
        return f"{y.split('.')[0]}-{int(month_part):02d}-{int(m.group(2)):02d}"
    return None

def y_to_month_start(y):
    """Convert y field to month start"""
    parts = y.split('.')
    if len(parts) == 2:
        return f"{parts[0]}-{int(parts[1]):02d}-01"
    return f"{parts[0]}-01-01"

# Add dt field to each event
updates = {}
for i, ev in enumerate(events):
    # Try URL first
    dt = extract_date_from_url(ev.get('u1', ''))
    if not dt:
        dt = extract_date_from_title(ev.get('t', ''), ev.get('y', ''))
    if not dt:
        # Extract from y field if contains specific info
        y = ev.get('y', '')
        if '.' in y:
            parts = y.split('.')
            year, month = parts[0], int(parts[1])
            # For "2025" style (no month), use year-01-01
            if len(parts) == 2 and 1 <= month <= 12:
                dt = f"{year}-{month:02d}-01"
            else:
                dt = f"{year}-01-01"
        else:
            dt = f"{y}-01-01"
    ev['dt'] = dt
    updates[i] = {'y': ev['y'], 'dt': ev['dt'], 't': ev['t'][:30]}
    print(f"  [{i:2d}] {ev['y']:>8s} → {dt}  | {ev['t'][:40]}")

# Now rebuild the ENF_EVENTS array
new_lines = []
new_lines.append('const ENF_EVENTS = [')
for i, ev in enumerate(events):
    # Build JSON line
    parts = []
    for key in ['y', 'dt', 't', 'tp', 'b', 'r', 'd']:
        val = ev.get(key, '')
        # Escape special chars for JS string
        val_escaped = val.replace('\\', '\\\\').replace('"', '\\"')
        parts.append(f'"{key}":"{val_escaped}"')
    for key in ['u1', 'l1']:
        if key in ev and ev[key]:
            val_escaped = ev[key].replace('\\', '\\\\').replace('"', '\\"')
            parts.append(f'"{key}":"{val_escaped}"')
    
    line = '  {' + ','.join(parts) + '},'
    new_lines.append(line)
new_lines.append('];')

new_arr_text = '\n'.join(new_lines)

# Replace in HTML
new_html = html[:start] + new_arr_text + html[end:]
with open('/tmp/regulatory-repo/index.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print(f"\nDone! Updated {len(events)} events with dt field")

# Also get the lines around renderDaily to see date display code
import subprocess
result = subprocess.run(['sed', '-n', '799,920p', '/tmp/regulatory-repo/index.html'], capture_output=True, text=True)
# Find all lines that show date in renderDaily
for line in result.stdout.split('\n'):
    if '📅' in line or 'y+' in line or 'y.' in line or 'ev.y' in line or 'dp.y' in line or 'nr.y' in line or 'p.y' in line:
        print(f"DATE DISPLAY: {line.strip()}")
