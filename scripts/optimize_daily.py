#!/usr/bin/env python3
"""一次性优化：Tab红点、时间范围筛选、NEW高亮、紧凑卡片"""
import re

with open('/tmp/regulatory-repo/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. 在 CSS 末尾加 tab-badge 样式
css_insert = '''
/* tab badge for new count */
.tab-badge{background:#ff5252;color:#fff;font-size:10px;padding:1px 6px;border-radius:8px;margin-left:4px;font-weight:600;min-width:16px;text-align:center;display:inline-block;vertical-align:middle}
.daily-filter{display:flex;gap:6px;margin-bottom:14px}
.daily-filter span{cursor:pointer;padding:5px 12px;border-radius:16px;font-size:13px;transition:all .15s}
.daily-filter span:hover{opacity:.85}
'''
html = html.replace('</style>', css_insert + '\n</style>')

# 2. 底部导航：在每日动态按钮后加 badge 元素
html = html.replace(
    '<button class="btn" id="navDaily" onclick="switchView(\'daily\')"><span class="bi">📢</span>每日动态</button>',
    '<button class="btn" id="navDaily" onclick="switchView(\'daily\')"><span class="bi">📢</span>每日动态<span id="dailyBadge" class="tab-badge" style="display:none"></span></button>'
)

# 3. 替换整个 renderDaily 函数（L798~L904）
# 先找到精确文本
old_renderDaily_start = html.index('function renderDaily(){var td=new Date()')
old_renderDaily_end = html.index('\nfunction showHome()', old_renderDaily_start)

new_renderDaily = '''
var _dailyFilter='30d';
function renderDaily(filter){
  if(filter){_dailyFilter=filter;localStorage.setItem('dailyFilter',filter);}
  else{
    var saved=localStorage.getItem('dailyFilter');
    if(saved)_dailyFilter=saved;
    updateDailyBadge();
  }
  var td=new Date(),today=td.getTime();
  var daysMap={'7d':7,'30d':30,'all':9999};
  var maxDays=daysMap[_dailyFilter]||30;
  // Combine all events, filter by date range
  var allEvents=[];
  for(var i=0;i<ENF_EVENTS.length;i++){
    var e=ENF_EVENTS[i];
    if(_dailyFilter!=='all'&&e.dt){
      var parts=e.dt.split('-');
      var ed=new Date(parseInt(parts[0]),parseInt(parts[1])-1,parseInt(parts[2])||1);
      var diffDays=(today-ed.getTime())/86400000;
      if(diffDays>maxDays)continue;
    }
    allEvents.push(e);
  }
  // Sort by dt desc
  allEvents.sort(function(a,b){return a.dt>b.dt?-1:a.dt<b.dt?1:0;});
  // Group by date
  var groups={};
  for(var i=0;i<allEvents.length;i++){
    var e=allEvents[i];var key=e.dt||'unknown';
    if(!groups[key])groups[key]=[];
    groups[key].push(e);
  }
  var dates=Object.keys(groups).sort().reverse();
  // Check if item is new
  function isNewItem(name){
    if(typeof _newLaws==='undefined'||!_newLaws||!_newLaws.length)return false;
    for(var k=0;k<_newLaws.length;k++){
      if(name.indexOf(_newLaws[k])>=0||_newLaws[k].indexOf(name)>=0)return true;
    }
    return false;
  }
  var html='<div style="margin-bottom:12px;">';
  html+='<h2 style="font-size:20px;margin-bottom:4px;">📢 每日合规动态</h2>';
  html+='<p style="font-size:13px;color:#888;margin-bottom:12px;">基于最新监管信息自动汇总，点击标题查看原文</p>';
  // Time filter tabs
  html+='<div class="daily-filter">';
  var filts=['7d','30d','all'];
  var flabels={'7d':'近7天','30d':'近30天','all':'全部'};
  for(var fi=0;fi<filts.length;fi++){
    var f=filts[fi];
    var active=_dailyFilter===f?'background:#1a73e8;color:#fff;font-weight:600;':'background:#e8eaf6;color:#333;font-weight:400;';
    html+='<span onclick="renderDaily(\\''+f+'\\')" style="'+active+'">'+flabels[f]+'</span>';
  }
  html+='</div></div>';
  // Loop dates
  for(var di=0;di<dates.length;di++){
    var date=dates[di];
    var items=groups[date];
    var dateLabel=date;
    if(date.length===10){
      var dp=date.split('-');
      dateLabel=parseInt(dp[1])+'月'+parseInt(dp[2])+'日';
    }
    var newCount=0;
    for(var si=0;si<items.length;si++){if(isNewItem(items[si].t))newCount++;}
    html+='<div style="margin-bottom:10px;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);">';
    html+='<div style="background:#f5f5f5;padding:7px 12px;font-size:13px;font-weight:600;color:#555;display:flex;justify-content:space-between;align-items:center;">';
    html+='<span>📅 '+dateLabel+'<span style="font-size:11px;color:#999;font-weight:400;margin-left:5px;">（'+items.length+'条）</span></span>';
    if(newCount>0)html+='<span style="background:#ff5252;color:#fff;font-size:11px;padding:1px 7px;border-radius:8px;font-weight:600;">'+newCount+'条新增</span>';
    html+='</div>';
    for(var ii=0;ii<items.length;ii++){
      var e=items[ii];
      var nw=isNewItem(e.t);
      var bc;
      if(e.tp.indexOf("新规")>=0)bc='#2e7d32';
      else if(e.tp.indexOf("行政")>=0||e.tp.indexOf("案例")>=0)bc='#c62828';
      else if(e.tp.indexOf("通报")>=0)bc='#1565c0';
      else bc='#6a1b9a';
      html+='<div style="background:#fff;padding:9px 12px;border-left:3px solid '+bc+';';
      if(ii<items.length-1)html+='border-bottom:1px solid #f0f0f0;';
      html+='">';
      html+='<div style="font-size:13px;font-weight:600;margin-bottom:2px;line-height:1.4;">';
      html+=(e.u1?'<a href="'+e.u1+'" target="_blank" rel="noopener" style="color:#1a73e8;text-decoration:none;">'+e.t+' ↗</a>':'<b>'+e.t+'</b>');
      html+='</div>';
      html+='<div style="font-size:11px;color:#888;margin:3px 0;display:flex;align-items:center;gap:5px;flex-wrap:wrap;">';
      var tpMap={'🆕':'#2e7d32','⚖':'#c62828','⚠':'#1565c0','📋':'#6a1b9a'};
      var tpColor=tpMap[e.tp.slice(0,2)]||'#888';
      html+='<span style="background:'+tpColor+';color:#fff;padding:1px 5px;border-radius:3px;font-size:10px;">'+e.tp+'</span>';
      html+='<span>📅 '+e.dt+'</span>';
      if(nw)html+='<span style="background:#ff5252;color:#fff;padding:1px 5px;border-radius:3px;font-size:10px;font-weight:600;">🆕 NEW</span>';
      html+='</div>';
      html+='<div style="font-size:12px;color:#555;margin:3px 0;line-height:1.5;">'+e.d+'</div>';
      html+='</div>';
    }
    html+='</div>';
  }
  if(dates.length===0)html+='<div style="text-align:center;padding:40px 0;color:#999;font-size:14px;">📭 所选时间范围内暂无动态</div>';
  html+='<div style="text-align:center;font-size:12px;color:#999;padding:16px 0 32px;">📧 每日合规报告已推送到内部邮件组 · <a href="https://tonyto424.github.io/regulatory-directory/" style="color:#1a73e8;">查看完整法规目录 →</a></div>';
  document.getElementById("dailyContent").innerHTML=html;
}
function updateDailyBadge(){
  var badge=document.getElementById("dailyBadge");
  if(!badge)return;
  var td=new Date(),today=td.getTime();
  var count=0;
  for(var i=0;i<ENF_EVENTS.length;i++){
    var e=ENF_EVENTS[i];
    if(!e.dt)continue;
    var p=e.dt.split('-');
    var ed=new Date(parseInt(p[0]),parseInt(p[1])-1,parseInt(p[2])||1);
    if((today-ed.getTime())/86400000<=7)count++;
  }
  if(count>0){badge.textContent=count;badge.style.display='inline-block';}
  else badge.style.display='none';
}
'''

html = html[:old_renderDaily_start] + new_renderDaily + html[old_renderDaily_end:]

# 4. 在 render() 调用后更新 badge
html = html.replace(
    'render();\n// Mark domains',
    'render();updateDailyBadge();\n// Mark domains'
)

# 5. 更新 switchView 中 daily 分支，传入过滤状态
html = html.replace(
    'else if(v=="daily"){document.getElementById("navDaily").classList.add("active");renderDaily();}',
    'else if(v=="daily"){document.getElementById("navDaily").classList.add("active");renderDaily();updateDailyBadge();}'
)

with open('/tmp/regulatory-repo/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done! Applied all optimizations.")
print(f"File size: {len(html)} bytes")
# Quick validation
assert 'updateDailyBadge' in html, "Missing updateDailyBadge"
assert '_dailyFilter' in html, "Missing _dailyFilter"
assert 'tab-badge' in html, "Missing tab-badge CSS"
print("All checks passed.")
