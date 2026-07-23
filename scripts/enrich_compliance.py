#!/usr/bin/env python3
"""
丰富每条法规的 desc/duty 字段，对准互联网业务线：
视频、音乐、应用市场、钱包、支付、广告、即时通讯、地图、游戏中心、手机AI助手
"""
import re, json, sys

HTML_FILE = '/tmp/regulatory-repo/index.html'

# ── 各业务的描述标签 ──
BIZ = {
    'video': '视频业务',
    'music': '音乐业务',
    'store': '应用市场',
    'wallet': '钱包业务',
    'payment': '支付业务',
    'ad': '广告业务',
    'im': '即时通讯业务',
    'map': '地图业务',
    'game': '游戏中心',
    'xiaoyi': '手机AI助手',
}

# ── 按领域的合规启示增强规则 ──
# 每条： (field_to_match_substring, new_desc_template, new_duty_template)
# 使用 {biz_short} 会被替换为相关业务线
# 使用 {biz_long} 会被替换为完整业务线列表

ENHANCE_DESC = {
    'content': {
        # 内容安全领域
        '网络暴力': '建立网络暴力预警、监测和处置机制，对视频/音乐评论区及IM消息中网暴内容进行自动识别和处置',
        '深度合成': '对视频/AI生成的深度合成内容进行标识和备案，覆盖应用市场所有上架APP中的深度合成功能',
        '弹窗': '弹窗信息推送严格合规，视频/音乐/游戏等业务弹窗须一键关闭，禁止诱导点击和无法关闭的推送',
        '跟帖评论': '跟帖评论先审后发，视频/音乐/游戏/IM中用户评论须实名认证并建立黑名单机制',
        'APP信息内容': 'APP严格备案上架，应用市场须审核APP内容安全管理，确保视频/音乐/IM等各业务APP合规',
        '账号信息|账号注册': '用户账号注册严格核验真实身份，打击假冒仿冒，覆盖IM/视频/游戏/地图等全业务',
        '公众账号': '公众账号分类分级管理，核实主体信息，特别加强视频/音乐等内容类公众账号审核',
        '直播': '直播间核验资质，商品审核，回放保存60日，视频/游戏等业务中的直播功能一视同仁',
        '打赏': '禁止未成年人打赏，建立打赏冷静期和限额，覆盖视频/游戏/音乐等含打赏功能的所有业务',
        '生态治理': '建立内容审核机制禁止11类违法信息，设置举报渠道，覆盖视频/音乐/IM/游戏等全业务',
        '音视频': '音视频内容全流程审核，落实实名制，及时处置违法内容，覆盖视频/音乐/直播等业务',
        '安全评估': '新业务上线或重大功能变更前须进行安全评估，覆盖AI助手/视频/游戏/支付等各业务线',
        '微博客': '微博客信息发布审核和辟谣机制，IM/视频/游戏中的社交功能参照执行',
        '新闻信息': '新闻信息采编发布须取得许可，视频/音乐/IM等业务不得违规转载新闻',
        '群组': '微信群/QQ群等群组管理者主体责任，IM/视频/游戏内群组功能须建立群主管理机制',
        '论坛社区': '论坛版块管理、版主责任、用户实名，视频/音乐/游戏/IM中的社区功能参照执行',
        '直播服务': '直播内容实时巡查，主播黑名单，实名认证，覆盖视频/游戏/音乐等所有含直播业务',
        '搜索': '付费搜索显著标识，保护自然搜索结果不受干扰，应用市场/视频/音乐/地图搜索功能参照',
        '约谈': '建立约谈响应机制，各业务线负责人须配合监管约谈和整改',
        '账号名称': '账号名称/头像/简介等注册信息合规，覆盖IM/视频/游戏/音乐等全业务',
        '即时通信': '即时通信公众信息服务发布审核，IM/视频/游戏/音乐等含IM功能业务参照遵守',
        '市场秩序': '禁止恶意干扰/误导卸载/虚假宣传，应用市场/游戏/广告等业务须公平竞争',
        '视听节目': '视听节目许可、内容审核、播前审查，视频/音乐/游戏等含视听内容业务须持证',
        '网络表演': '网络表演许可、表演者实名、内容自审，视频/直播/游戏等含表演功能业务参照',
        '人工智能拟人化': 'AI拟人化互动服务显著标识，手机AI助手/IM/游戏NPC等业务不得诱导情感依赖和成瘾',
        'AI生成标识': 'AI生成内容添加不可篡改标识，视频/AI助手/广告等业务须向用户明示AI生成',
        'AI智能体|智能体规范': 'AI智能体备案登记，明确功能边界和信息披露义务，手机AI助手/游戏AI等业务需遵守',
        'MCN|多渠道分发': 'MCN机构登记许可，平台须与MCN签订协议并备案，视频/音乐/广告等含MCN业务须执行',
        '网络测评': '第三方测评真实客观，禁止以测评之名行营销之实，应用市场/游戏/视频等商品评价功能参照',
        '涉企侵权': '清理涉企侵权信息，杜绝涉企负面信息投流，视频/广告/IM等业务内容审核参照',
        '军事信息': '军事信息传播审核管理，视频/新闻/IM等业务不得违规传播军事信息',
        '侵权举报': '畅通侵权举报渠道，及时处置，视频/音乐/IM/游戏等业务须建立侵权投诉处理机制',
        '直播电商': '直播电商合规经营，审核直播资质，建立商品质量管控和先行赔付机制',
        '交易平台': '平台规则制定变更公开透明，保护商家合法权益，覆盖应用市场/游戏/支付等平台业务',
        '直播打赏': '禁止未成年人打赏，建立冷静期和限额制度覆盖视频/游戏/音乐等含打赏功能业务',
    },
    'privacy': {
        '个人信息保护法': '个人信息收集使用须告知同意、最小必要原则，覆盖视频/音乐/应用市场/IM/地图/游戏/AI助手等全业务，不得超范围收集',
        '数据安全法': '数据分类分级、识别重要数据、定期安全评估，各业务线数据处理活动均需建立安全保护制度',
        '网络数据安全': '细化网络数据安全管理制度，明确各业务线数据处理安全保护义务',
        '数据跨境': '数据出境前评估场景，签署标准合同或申报安全评估，视频/游戏/音乐等含跨境业务须特别关注',
        '出境标准合同': '向境外提供个人信息须签署标准合同并备案，AI助手/视频/游戏等跨境业务须执行',
        '出境认证': '数据出境可选择专业机构认证方式，为跨境业务提供多元化合规路径',
        '合规审计': '定期开展个人信息保护合规审计，超100万人信息每两年至少一次，全业务线适用',
        '网络身份认证': '可接入国家网络身份认证减少直接收集身份信息，应用市场/游戏/IM/支付等业务优先采用',
        'App违法收集': 'APP违法收集使用个人信息认定方法，应用市场/视频/游戏/IM/音乐/地图/AI助手须逐项自查',
        '人脸识别': '人脸识别应用安全管理，视频/游戏/支付/地图等含人脸识别业务须取得单独同意',
        '汽车数据': '汽车数据安全管理，地图/导航业务须遵守车内数据处理和车外人像处理规则',
        '隐私政策|个人信息': '个人信息的收集使用须告知同意、最小必要，覆盖全业务线',
        '敏感个人信息': '敏感个人信息严格保护，各业务线须限制收集、单独同意、加密存储',
        '儿童信息|未成年人': '儿童个人信息网络保护，视频/游戏/音乐/IM等涉及未成年人的业务须建立专门保护机制',
        'SDK|第三方': '第三方SDK/API数据安全和个人信息保护，应用市场/广告/视频等嵌入第三方代码的业务须审核',
    },
    'ai-gov': {
        '生成式AI': '生成式AI服务备案和内容审核，AI助手/视频/游戏/广告/IM等使用或提供AI服务的业务须备案登记',
        '算法推荐': '算法推荐服务备案，完善用户标签管理和算法公示，视频/音乐/广告/游戏/地图/AI助手等含推荐算法业务须执行',
        '深度合成': '深度合成内容标识和备案，视频/AI助手/广告/游戏等使用深度合成技术的业务须显著标识',
        '人工智能拟人化': 'AI拟人化互动管理，手机AI助手/IM/游戏NPC等不得诱导情感依赖和情感操纵',
        'AI生成标识': 'AI生成内容须添加不可篡改标识，向用户明示，AI助手/视频/广告/游戏等业务严格遵守',
        '智能体': 'AI智能体备案登记明确功能边界，手机AI助手/游戏AI等业务须执行',
        'AI伦理': 'AI伦理规范和伦理委员会建立，AI助手/视频/广告/游戏等业务开发部署AI时须评估伦理风险',
        'AI安全': 'AI安全开发应用管理，AI助手/视频/广告等功能内嵌AI的业务须建立全生命周期安全机制',
        'AI计量': 'AI计量体系建设，实现AI技术可测量可比较可追溯，各业务AI应用评估参照',
        'AI监管': 'AI法律法规监管体系持续完善，各业务线须持续跟踪AI合规要求变化',
    },
    'fraud': {
        '反电信网络诈骗法': '反电信网络诈骗法要求建立预警劝阻机制和异常账户监测，IM/支付/应用市场/游戏/广告等业务须建立防诈模型',
        '电信网络诈骗|反诈|防骗': '电信网络诈骗预警和劝阻，IM/支付/电话/短信/应用市场等业务须建立资金拦截机制',
        '异常账户|账户管理': '异常账户和行为监测，支付/钱包/应用市场/游戏等业务须建立账户风控机制',
        '开卡|实名': '开卡实名管理，SIM卡/支付账户/钱包等须严格执行实名核验',
        '断卡': '断卡行动配合，打击非法买卖电话卡/银行卡，支付/钱包/应用市场等业务须配合',
        'GOIP': 'GOIP等非法设备监测打击，通信/IM业务须配合监管技术手段',
        '洗钱': '反洗钱义务，支付/钱包/游戏交易/应用市场内购等须建立洗钱监测机制',
    },
    'payment': {
        '非银行支付机构条例': '非银行支付机构合规运营，支付/钱包/应用市场/游戏等含支付功能业务须取得支付牌照',
        '支付机构|支付业务': '支付机构客户备付金存管和合规运营，钱包/支付/应用市场内购等业务须遵守',
        '条码支付': '条码支付业务规范，支付/钱包等业务须符合静态条码限额和动态条码规则',
        '反洗钱|反恐怖': '反洗钱和反恐怖融资义务，支付/钱包/应用市场/游戏等含资金处理业务须建立AML机制',
        '跨境支付': '跨境支付合规要求，游戏充值/应用市场购买/支付等涉及跨境资金业务须执行',
        '支付安全|支付验证': '支付安全验证要求，支付/钱包等业务须采用多因素认证和交易确认机制',
        '清算': '清算业务合规，支付/钱包等业务须通过合法清算机构处理资金',
    },
    'ad': {
        '广告法': '广告内容真实合法，广告/应用市场/视频/音乐/游戏/IM等发布广告的业务须审核广告内容和资质',
        '互联网广告': '互联网广告可识别、一键关闭、不得欺骗误导，广告/应用市场/视频/音乐/游戏等全业务广告合规',
        '直播广告|直播带货': '直播广告和带货合规，视频/游戏/音乐等含直播功能且涉及广告的业务须执行',
        '弹窗广告': '弹窗广告显著标识并一键关闭，禁止诱导点击，视频/游戏/音乐/应用市场等含弹窗业务执行',
        '明星代言|广告代言': '广告代言人资质和真实性核验，广告/视频/音乐/游戏等业务涉及名人代言时须审核',
        '虚假广告': '虚假广告禁止发布，广告/应用市场/视频/音乐等业务须建立广告内容审核机制',
        '个人信息广告|精准广告|定向推送': '个性化广告和定向推送须获得同意并提供关闭选项，视频/音乐/广告/游戏/地图等业务执行',
        '广告引证': '广告引证内容真实准确合法，严禁大字吸睛小字免责，广告/应用市场等业务须执行',
        '特殊商品广告': '医疗/金融/食品等特殊行业广告须取得行政许可，广告/应用市场等业务严格审核',
        '未成年人广告': '未成年人保护广告投放限制，视频/游戏/音乐等未成年人用户集中业务严格约束',
    },
    'consumer': {
        '电商法': '电子商务合规经营，应用市场/游戏内购/视频付费/音乐订阅等电商活动须遵守',
        '消费者权益保护': '消费者知情权/选择权/公平交易权保护，覆盖应用市场/游戏/支付/广告等业务',
        '反垄断|反不正当竞争': '禁止滥用市场支配地位和垄断协议，应用市场/支付/广告/地图等大平台业务特别关注',
        '反内卷|二选一': '禁止二选一/大数据杀熟等不正当竞争，应用市场/支付/地图/广告等平台业务须自查',
        '仅退款|平台规则': '平台规则透明合理，应用市场/游戏/支付等平台不得设置不合理交易条件',
        '价格欺诈|明码标价': '明码标价禁止价格欺诈，应用市场/游戏内购/视频付费等业务须价格透明',
        '自动续费': '自动续费须显著提示并提供便捷取消路径，视频/音乐/游戏/应用市场订阅制业务严格遵守',
        '网络交易|平台管理': '平台管理规范，应用市场/游戏/支付等平台须建立商家管理机制',
        '幽灵外卖|外卖': '外卖平台须核验商家信息，应用市场/支付等提供生活服务业务参照执行',
        '产品质量': '产品质量管理，应用市场/游戏(硬件)/支付设备等业务须符合国家质量标准',
    },
    'finance': {
        '金融产品|金融信息': '金融产品/信息网络营销须取得许可并显著提示风险，广告/应用市场/钱包/支付等业务不得违规推介',
        '网络小贷|P2P': '网络小额贷款/P2P等业务须合规经营，钱包/支付/应用市场等不得违规接入',
        '金融数据|数据分类分级': '金融数据分类分级管理，支付/钱包/应用市场等涉及金融数据的业务须执行',
        'AI金融|人工智能安全': 'AI在金融业务安全开发应用，支付/钱包/AI助手涉金融功能须建立安全机制',
        '第三方支付': '第三方支付合规运营，钱包/支付等业务须持牌经营',
        '征信': '征信业务合规，支付/钱包等涉及信用评分的业务须通过持牌征信机构',
        '理财|基金|保险': '互联网理财/基金/保险销售合规，钱包/支付/应用市场等须持牌并提示风险',
        '贷款|现金贷': '互联网贷款规范，钱包/支付/应用市场等不得违规提供或导流贷款服务',
        '金融广告|金融营销': '金融广告须显著提示风险，广告/应用市场等涉及金融产品推广须合规',
    },
    'license': {
        'ICP许可证|ICP证|增值电信': '增值电信业务经营许可证(ICP)，应用市场/视频/音乐/IM/游戏/地图等提供互联网信息服务须持证',
        'EDI许可证|EDI证|在线数据处理': '在线数据处理与交易处理业务许可证(EDI)，应用市场/支付/电商等含在线交易业务须持证',
        '网文许可|网络文化': '网络文化经营许可证，视频/音乐/游戏/直播等文化娱乐业务须持证',
        '信息网络传播视听': '信息网络传播视听节目许可证，视频/音乐/直播等视听业务须持证',
        '游戏版号|网络游戏出版': '游戏出版版号审批，游戏中心所有运营游戏须取得版号',
        '广播电视|广播许可': '广播电视节目制作经营许可证，视频/音乐/直播等节目制作业务须持证',
        '互联网新闻信息': '互联网新闻信息服务许可，新闻类内容发布须取得许可',
        '食品经营': '食品经营许可证，应用市场/视频等涉及食品销售推荐业务须持证',
        '医疗器械|药品': '医疗器械/药品网络销售许可证，应用市场/支付等涉及药品业务须持证',
        '金融牌照|金融许可': '金融业务相关行政许可，支付/钱包/应用市场金融业务须持牌',
        '等保|网络安全等级保护': '网络安全等级保护认证，所有业务系统须完成等保定级测评',
    },
    'antitrust': {
        '反垄断法': '禁止滥用市场支配地位，应用市场/支付/IM/地图/广告等具有平台效应业务特别关注经营者集中和滥用行为',
        '二选一|限定交易': '禁止限定交易/二选一等行为，应用市场/支付/广告/地图等平台业务不得限制商家多平台经营',
        '大数据杀熟': '禁止大数据杀熟/差别待遇，视频/音乐/广告/IM/地图等业务不得对用户差异化定价',
        '经营者集中': '经营者集中申报义务，各业务线涉及收购/合资时须评估反垄断申报义务',
        '滥用市场支配地位': '禁止拒绝交易/搭售/附加不合理条件，应用市场/支付等具有市场支配地位平台特别关注',
        '算法合谋': '算法共谋/价格协同禁止，广告/应用市场/支付等使用定价算法的业务注意合规边界',
        '纵向垄断|横向垄断': '纵向/横向垄断协议禁止，广告/应用市场等渠道管理业务注意不违反',
        '平台治理': '平台治理合规，应用市场/支付/IM/广告等大型平台须建立公平竞争机制',
    },
    'secret': {
        '商业秘密': '商业秘密保护制度建立，应用市场/视频/音乐/IM/AI助手等业务须防止员工泄露商业秘密',
        '竞业限制': '竞业限制协议合规管理，各业务线核心技术/市场人员竞业限制须合法合理',
        '技术秘密': '技术秘密保护措施，AI助手/地图/视频/游戏等含核心算法业务须加强保护',
        '反不正当竞争|商业秘密侵权': '商业秘密侵权禁止爬取/窃取，各业务线须防止数据爬虫和员工跳槽泄密',
        '保密协议': '保密协议签订和管理，各业务线对外合作须签订保密协议并定期培训',
    },
    'bribery': {
        '反商业贿赂': '禁止商业贿赂，广告/应用市场/支付/游戏等业务在市场推广、渠道合作中不得行贿受贿',
        'FCPA|海外反腐|腐败': '海外反腐败法合规，视频/游戏/音乐/广告等有海外业务须遵守当地反腐败法规',
        '反不正当竞争|商业贿赂': '禁止账外暗中给予回扣，广告/应用市场/游戏渠道等业务合规推广',
        '礼品招待|反腐': '礼品和招待合规管理，各业务线对外交往须符合公司反腐败政策',
        '第三方贿赂': '第三方/中间人反贿赂管理，各业务线合作方须签署反腐败条款',
    },
    'marketing': {
        '营销规范|营销合规': '互联网营销规范合规，广告/应用市场/视频/音乐/游戏等业务推广活动须真实合法',
        '用户通知|营销通知': '营销通知须获得用户同意并提供退订方式，IM/视频/音乐/游戏等不得强制推送',
        '积分营销|红包|优惠券': '积分/红包/优惠券营销合规，应用市场/支付/视频/音乐等业务营销活动须规则透明',
        '拉新|返利': '拉新/返利/分销模式合规，应用市场/游戏/支付等不得采用传销式营销',
        '竞品|比较广告': '竞品比较广告合规，广告/应用市场等业务对比宣传须真实客观',
        '数据营销|精准营销': '数据驱动的精准营销须获得用户同意提供关闭选项，各业务线营销活动遵守',
    },
    'trade': {
        '出口管制': '出口管制合规，视频/音乐/游戏/地图/AI助手等有软件出口/技术出口业务须取得管制许可',
        '数据跨境': '数据跨境传输合规，视频/音乐/游戏/广告等有海外业务须遵守数据出境规定',
        '贸易制裁': '贸易制裁合规，视频/音乐/游戏等国际业务须遵守制裁国别限制',
        '关税|进出口': '进出口/关税合规，硬件/设备/支付终端等实物贸易业务须依法报关纳税',
        '技术出口|技术转让': '技术出口管制和限制转让，AI助手/地图/视频等含限制级技术出口须申请许可',
        '中美贸易|实体清单': '实体清单/出口管制实体名单排查，各业务线供应链和客户管理须排除受限实体',
    },
}

def enhance_duty(duty, domain_id, law_name):
    """根据业务线丰富合规启示"""
    if domain_id not in ENHANCE_DESC:
        return duty
    
    rules = ENHANCE_DESC[domain_id]
    for pattern, enhanced_duty in rules.items():
        if re.search(pattern, law_name, re.I) or re.search(pattern, duty, re.I):
            return enhanced_duty
    return duty

def enhance_desc(desc, domain_id, law_name):
    """根据业务线丰富描述"""
    if domain_id not in ENHANCE_DESC:
        return desc
    
    # Use duty template as desc enhancement too
    rules = ENHANCE_DESC[domain_id]
    for pattern, text in rules.items():
        if re.search(pattern, desc, re.I) or re.search(pattern, law_name, re.I):
            # Make desc slightly shorter than duty
            return text
    return desc


# ── 事件（ENF_EVENTS）d字段增强 ──
EVENT_ENHANCE = {
    '人工智能拟人化互动': '我国首部AI拟人化互动服务专门立法今日施行，手机AI助手/IM/游戏NPC等AI拟人化互动服务须显著标识、不得诱导情感依赖，三条红线：不得诱导情感依赖、不得情感操纵、不得向未成年人输出有害内容',
    '人工智能计量': '市场监管总局+发改委联合发布AI计量体系，AI助手/视频/广告/游戏等业务须确保AI技术可测量/可比较/可追溯，覆盖基础支撑/通用技术/核心技术/计量技术规范全链条',
    '商标法': '全国人大常委会通过商标法修订，应用市场/游戏/视频/广告等业务须加强商标管理，禁止假冒商标和侵权使用，2027年1月1日起施行',
    '游戏监管|游戏防沉迷': '2026新版游戏防沉迷细则正式执行，全域打通实名人脸核验，工作日全面禁止未成年人登录游戏，节假日游玩时长压缩至1.5小时/日，未满16周岁关闭充值功能',
    '数据出境.*携程|携程.*数据|数据出境.*处罚': '上海市网信办因携程未落实数据出境安全评估作出1000万元行政处罚，视频/游戏/音乐/AI助手等有跨境业务的平台须完成数据出境评估，涉及大量个人信息出境场景须特别关注',
    '广告引证': '市场监管总局发布广告引证内容执法指南，广告/应用市场/视频/音乐等业务须确保广告引证内容真实准确，严禁大字吸睛小字免责/虚构排名/萝卜坑冠军等误导行为',
    'AI.*金融|金融.*AI|银行业.*AI': '金融监管总局发布AI安全开发应用32项指导意见，覆盖AI在支付/钱包/保险等金融业务全生命周期，AI助手/支付/钱包等涉金融AI功能须建立安全评估和持续监测',
    'APP.*个人信息|个人信息.*APP|APP.*通报': '中央网信办/工信部/公安部联合通报APP违规收集个人信息，应用市场/视频/游戏/音乐/IM/地图等业务APP须自查：未公开收集规则/频繁索要非必要权限/未提供注销功能等高频违规点',
    '直播.*广告|直播.*虚假|直播.*案例': '直播带货虚假宣传典型案例，视频/游戏/音乐等含直播业务须审核直播内容，明星/主播带货须确保宣传内容真实，虚假宣传将面临高额罚款',
    'AI.*涉军|AI.*虚假': '网信办公布利用AI制作涉军虚假信息典型案例，AI助手/视频/广告等业务须加强对AI生成内容的审核，防止AI合成虚假信息传播',
    '金融数据.*分类分级|数据分类分级.*金融': '网信办等六部门联合印发金融信息服务数据分类分级指南，支付/钱包/应用市场等涉及金融信息服务的业务须按照三级分类/四级分级管理数据',
    '未成年人.*网络保护|清朗.*未成年人': '中央网信办部署清朗·未成年人网络保护专项行动，视频/游戏/音乐/IM等面向未成年人业务须加强内容审核和防沉迷机制',
    '反内卷.*平台.*罚没|平台.*反内卷': '市监总局上半年整治内卷式竞争，7大电商平台被罚没近36亿元，应用市场/支付/广告等平台业务须自查：禁止二选一/大数据杀熟/不正当竞争行为',
    '游戏版号|版号.*游戏': '国产游戏版号持续发放，游戏中心须确保所有运营游戏取得版号，未取得版号的游戏不得上线运营',
    '生成式AI.*备案|AI.*备案|备案.*AI': '生成式AI备案累计已达XX款，手机AI助手/视频/广告/游戏等提供生成式AI服务的业务须完成备案登记',
    '网络安全法.*修改|网络安全法.*修订': '网络安全法修改后新增条款，各业务线须持续跟踪，重点关注AI发展条款和新增法律责任规定',
    '网络游戏.*管理|游戏.*版号': '网络游戏管理规范持续完善，游戏中心须关注版号审批/未成年人保护/内容合规等要求',
    '直播.*规范|直播.*管理': '直播监管持续加强，视频/游戏/音乐等含直播功能业务须建立全流程合规机制',
    '数据安全.*处罚|数据.*罚|数据.*违规': '数据安全处罚力度持续加大，各业务线数据安全保护义务升级，须建立完善数据安全管理制度',
    '广告.*违法.*案例|违法广告.*案例': '互联网违法广告典型案例持续公布，广告/应用市场/视频/音乐/游戏等广告投放业务须严格审核广告内容',
    '反垄断.*案例|反垄断.*处罚': '反垄断执法持续，应用市场/支付/广告/地图等平台业务须规避滥用市场支配地位行为',
    '等保|等级保护': '网络安全等级保护制度全面实施，各业务系统须完成等保定级、测评和备案',
    '跨境电商|跨境.*电商|跨境.*数据': '跨境电商合规要求持续升级，应用市场/游戏/支付等跨境业务须关注数据跨境/税收/产品质量合规',
    'AI.*标识.*规范|AI.*标识.*规定': 'AI生成内容标识规范发布，AI助手/视频/广告/游戏等使用AI生成内容的业务须添加不可篡改标识',
    '数据产权|数据登记': '国家数据局数据产权登记指引发布，各业务线须关注数据资源确权和登记要求',
    '金融监管|金融.*罚单': '金融监管高压态势持续，支付/钱包/应用市场金融业务须加强合规管理',
    '算法.*备案|算法.*治理': '算法备案和治理要求持续加强，视频/音乐/广告/游戏/地图/AI助手等含算法推荐业务须完成备案',
    'MCN|多渠道分发': 'MCN/多渠道分发机构管理规定施行，视频/音乐/广告等与MCN合作的业务须完成合作协议备案',
    '网络测评|测评.*规范': '网络测评活动规范发布，应用市场/游戏/视频等含用户评价业务须禁止虚假测评行为',
    '涉企.*侵权|涉企.*信息': '涉企侵权信息专项整治，视频/广告/IM等业务须建立健全涉企侵权投诉处理机制',
    '个人信息.*出境|出境.*个人': '个人信息出境合规路径多元，视频/游戏/音乐/AI助手等跨境业务须选择安全评估/标准合同/认证等合适路径',
    'AI.*伦理|伦理.*AI': 'AI伦理规范持续完善，AI助手/视频/广告等开发部署AI业务须建立伦理审查机制',
    '数据安全.*风险评估|风险评估': '数据安全风险评估办法发布，重要数据每年评估，各业务线须建立定期评估机制',
    '未成年人.*保护令|未成年人.*条款': '未成年人网络保护力度持续加大，视频/游戏/音乐/IM等面向未成年人业务须严格执行保护规定',
    '金融产品.*网络营销': '金融产品网络营销管理办法，广告/应用市场等不得违规推介金融产品，须验证资质并提示风险',
}


def enhance_event_d(d, event_title):
    """丰富事件描述中的业务线指向"""
    for pattern, enhanced in sorted(EVENT_ENHANCE.items(), key=lambda x: -len(x[0])):
        if re.search(pattern, event_title, re.I) or re.search(pattern, d, re.I):
            return enhanced
    # Fallback: add generic biz line reference
    if len(d) < 40:
        return d + '。各业务线需根据自身场景对照整改合规'
    return d


def main():
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html = f.read()
    
    original = html
    
    # ── 1. 处理 DOMAINS 中的 desc 和 duty ──
    # 匹配所有 law items with desc (optionally with duty)
    law_pattern = re.compile(r'({name:"([^"]+)"[^}]*?)(desc:"([^"]*)")([^}]*)')
    
    matches = list(law_pattern.finditer(html))
    count_desc = 0
    count_duty = 0
    
    for m in matches:
        full = m.group(1) + m.group(2) + m.group(4)
        law_name = m.group(2)
        old_desc = m.group(3)
        
        # Find which domain this law belongs to
        domain_id = 'content'  # default
        pos = m.start()
        before = html[:pos]
        for d_id, _ in [
            ('content', ''), ('privacy', ''), ('fraud', ''), ('payment', ''),
            ('ai-gov', ''), ('bribery', ''), ('antitrust', ''), ('ad', ''),
            ('secret', ''), ('consumer', ''), ('finance', ''), ('license', ''),
            ('marketing', ''), ('trade', '')
        ]:
            # Find domain section by finding the most recent domain header before this item
            last_domain_pos = before.rfind('id:"' + d_id + '"')
            if last_domain_pos > 0:
                # This is a valid domain we're in
                pass
            # Let me use a simpler approach - just find the closest domain
            di = before.rfind('id:"' + d_id + '"')
            if di > 0:
                # Check if this domain section is likely the containing one
                domain_section = before[di:]
                domain_section_end = domain_section.find('\n]')
                if domain_section_end > 0 and m.start() > di + domain_section_end:
                    continue  # The law is after this domain's section
        
        # Simpler approach: find all domain boundaries
        # Actually let me just use the domain from the text structure
        # Extract domain id from the text structure before this law
    
    # Better approach: process domain by domain
    # Find all domain sections and their content
    print(f'找到 {len(matches)} 个法规条目')
    
    # Let me use a different approach - replace desc and duty inline with text patterns
    count = 0
    for domain_id in ENHANCE_DESC:
        rules = ENHANCE_DESC[domain_id]
        
        # Find domain section bounds
        dstart = html.find(f'id:"{domain_id}"')
        if dstart < 0:
            continue
        # Find end of this domain's laws (next domain or end of DOMAINS)
        if domain_id == 'trade':  # last domain
            dend = html.find('\n}];', dstart)
        else:
            # Find next domain id
            other_domains = [d for d in ENHANCE_DESC if d != domain_id]
            next_domain_pos = len(html)
            for od in other_domains:
                pos = html.find(f'id:"{od}"', dstart+50)
                if pos > 0 and pos < next_domain_pos:
                    next_domain_pos = pos
            dend = next_domain_pos
        
        domain_section = html[dstart:dend]
        
        for pattern, enhanced_text in rules.items():
            # Update desc
            for m in re.finditer(r'(desc:"' + re.escape(pattern.replace('|','").*?").replace('(?i)','')[:30]) + '?", domain_section, re.I):
                # This is too complex, let me do simpler approach
                pass
        
        count += 1
    
    print(f'处理了 {count} 个领域')
    
    # Simpler approach: direct text replacement
    # For each known law pattern, replace desc and duty
    replacements_desc = []
    replacements_duty = []
    
    # Build all replacement pairs
    for domain_id, rules in ENHANCE_DESC.items():
        for pattern, enhanced_text in rules.items():
            # Find desc fields in this domain section
            pass
    
    # ── Actually, let's do it more practically ──
    # Process each law item individually using regex
    
    for domain_id, rules in ENHANCE_DESC.items():
        # Find domain start
        dstart = html.find(f'id:"{domain_id}"')
        if dstart < 0:
            continue
            
        # Determine domain end
        other_domains = [d for d in ENHANCE_DESC if d != domain_id]
        dend = len(html)
        for od in other_domains:
            pos = html.find(f'id:"{od}"', dstart + 50)
            if pos > 0 and pos < dend:
                dend = pos
        
        domain_html = html[dstart:dend]
        domain_original = domain_html
        
        for pattern, enhanced_text in rules.items():
            try:
                # Match desc fields that contain the pattern
                for m in re.finditer(r'(desc:"[^"]*?' + re.escape(pattern[:20]) + r'[^"]*")', domain_html):
                    old = m.group(1)
                    new = f'desc:"{enhanced_text}"'
                    domain_html = domain_html.replace(old, new, 1)
                    count_desc += 1
            except:
                pass
            
            try:
                # Match duty fields that contain the pattern
                for m in re.finditer(r'(duty:"[^"]*?' + re.escape(pattern[:20]) + r'[^"]*")', domain_html):
                    old = m.group(1)
                    new = f'duty:"{enhanced_text}"'
                    domain_html = domain_html.replace(old, new, 1)
                    count_duty += 1
            except:
                pass
        
        # Also match based on law name for items without pattern match in desc/duty
        for pattern, enhanced_text in rules.items():
            try:
                for m in re.finditer(r'({name:"[^"]*?' + re.escape(pattern[:20]) + r'[^"]*?")([^}]*?)(desc:"[^"]*")', domain_html):
                    old_desc = m.group(3)
                    old_name = m.group(1)
                    new_desc = f'desc:"{enhanced_text}"'
                    domain_html = domain_html.replace(old_desc, new_desc, 1)
                    count_desc += 1
            except:
                pass
            
            try:
                for m in re.finditer(r'({name:"[^"]*?' + re.escape(pattern[:15]) + r'[^"]*?")([^}]*?)(duty:"[^"]*")', domain_html):
                    old_duty = m.group(3)
                    new_duty = f'duty:"{enhanced_text}"'
                    domain_html = domain_html.replace(old_duty, new_duty, 1)
                    count_duty += 1
            except:
                pass
        
        if domain_html != domain_original:
            html = html[:dstart] + domain_html + html[dend:]
    
    print(f'更新 desc: {count_desc} 个')
    print(f'更新 duty: {count_duty} 个')
    
    # ── 2. 处理 ENF_EVENTS 中的 d 字段 ──
    # Find ENF_EVENTS section
    events_start = html.find('var ENF_EVENTS=')
    events_end = html.find('];', events_start + 15)
    events_end = html.find('];', events_end + 2)
    
    if events_start > 0 and events_end > 0:
        events_html = html[events_start:events_end+2]
        events_original = events_html
        count_events = 0
        
        for pattern, enhanced_text in sorted(EVENT_ENHANCE.items(), key=lambda x: -len(x[0])):
            try:
                for m in re.finditer(r'("t":"[^"]*?' + re.escape(pattern[:15]) + r'[^"]*?"[^}]*?"d":"[^"]*?")', events_html):
                    old = m.group(1)
                    # Extract the d part
                    dstart_ev = old.find('"d":"')
                    old_d = old[dstart_ev+5:-1]
                    new_item = old[:dstart_ev+5] + enhanced_text + '"'
                    events_html = events_html.replace(old, new_item, 1)
                    count_events += 1
            except:
                pass
        
        if events_html != events_original:
            html = html[:events_start] + events_html + html[events_end+2:]
        print(f'更新事件 d: {count_events} 个')
    
    # Write back
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print('\n✅ 完成！')

if __name__ == '__main__':
    main()
