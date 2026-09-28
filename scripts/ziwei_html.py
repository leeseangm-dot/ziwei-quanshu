#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""紫微斗数命盘 HTML 渲染（零第三方依赖，仅标准库）。

由 ziwei_pan.py 调用，把排盘结果渲染为一份自包含的单文件 HTML：
  - 4×4 十二宫盘（传统方位：巳午未申 / 辰··酉 / 卯··戌 / 寅丑子亥）
  - 基本信息、四化、大限、小限、童限、当前运限、警告
  - 判读槽位（slot）：由 --interpret 注入 agent 撰写的判读文字

设计原则：
  1. 排盘数据全部由脚本算出，HTML 只是表现形式 —— 不手写盘面。
  2. 输出单文件、内嵌 CSS、无外部依赖，可直接分享 / 打印为 PDF。
  3. 判读与排盘解耦：脚本负责「准」，判读由模型负责「懂」。
"""

import re

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 传统命盘方位：地支在 4×4 网格中的位置（行, 列），1 起。
# 寅居左下，顺时针 寅→卯→…→丑
ZHI_GRID = {
    "巳": (1, 1), "午": (1, 2), "未": (1, 3), "申": (1, 4),
    "辰": (2, 1), "酉": (2, 4),
    "卯": (3, 1), "戌": (3, 4),
    "寅": (4, 1), "丑": (4, 2), "子": (4, 3), "亥": (4, 4),
}

MUTAGEN_CLS = {"禄": "lu", "权": "quan", "科": "ke", "忌": "ji"}
MUTAGEN_CN = {"禄": "化禄", "权": "化权", "科": "化科", "忌": "化忌"}

# 判读槽位：(键, 标题, 提示语)
SLOTS = [
    ("ming_shen", "一、命身与格局",
     "命宫／身宫主星庙陷、三方四正会照、格局判定。"),
    ("sihua", "二、四化与生克",
     "生年四化落宫、四化互相牵制、忌星所冲。"),
    ("shiergong", "三、十二宫分述",
     "逐一论断命、兄、夫、子、财、疾、迁、友、官、田、福、父母十二宫。"),
    ("yunxian", "四、运限推演",
     "当前大限、小限、流年，以及羊陀迭并、七杀重逢等叠加。"),
    ("zongjie", "五、综合论断",
     "总评命格高下、宜忌与可行建议。"),
]

CSS = r"""
:root{
  --ink:#241f1a; --ink-2:#4e463c; --ink-3:#8a7f72; --ink-4:#a89e90;
  --paper:#f6f2e9; --paper-2:#fffdf8;
  --line:#d6cab3; --line-2:#e8dfcd;
  --red:#9e2318; --red-2:#c0523c;
  --gold:#a8801f; --gold-2:#d0ab52;
  --green:#37693f; --purple:#63417f; --blue:#2a608f; --gray:#9a9186;
  --shadow:0 1px 2px rgba(60,45,25,.05),0 10px 28px -14px rgba(60,45,25,.16);
}
*{box-sizing:border-box;}
html{-webkit-text-size-adjust:100%;}
body{
  margin:0; padding:34px 18px 68px;
  background:
    radial-gradient(circle at 12% 6%, #fffdf8 0%, transparent 45%),
    radial-gradient(circle at 88% 94%, #f1eadc 0%, transparent 50%),
    var(--paper);
  color:var(--ink);
  font-family:"Songti SC","STSong","Noto Serif CJK SC","Source Han Serif SC",Georgia,"Microsoft YaHei",serif;
  font-size:15px; line-height:1.85;
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
}
.wrap{max-width:1140px;margin:0 auto;}

/* ---------- 头部 ---------- */
header{text-align:center;padding-bottom:24px;border-bottom:2px double var(--line);margin-bottom:30px;}
h1{font-size:31px;letter-spacing:.3em;margin:0 0 7px;font-weight:600;text-indent:.3em;line-height:1.5;}
.sub{color:var(--ink-3);letter-spacing:.16em;font-size:13.5px;}
.seal{
  display:inline-block;margin-top:14px;padding:4px 14px;border:1px solid var(--red-2);
  color:var(--red);font-size:12.5px;letter-spacing:.2em;border-radius:2px;
  background:rgba(158,35,24,.04);
}

/* ---------- 基本信息 ---------- */
.meta{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1px;
  background:var(--line-2);border:1px solid var(--line-2);margin-bottom:34px;
  border-radius:4px;overflow:hidden;
}
.meta div{background:var(--paper-2);padding:12px 16px;font-size:14px;}
.meta span{display:block;color:var(--ink-4);font-size:12px;letter-spacing:.12em;margin-bottom:3px;}
.meta b{font-weight:600;color:var(--ink);letter-spacing:.03em;}

/* ---------- 命盘 ---------- */
.sec-title{
  font-size:19px;letter-spacing:.18em;margin:38px 0 17px;padding-left:14px;
  border-left:3px solid var(--red-2);font-weight:600;line-height:1.5;
}
.sec-title:first-of-type{margin-top:8px;}
.chart{
  display:grid;grid-template-columns:repeat(4,1fr);
  grid-template-rows:repeat(4,minmax(174px,auto));gap:1px;
  background:var(--line);border:2px solid var(--ink);padding:1px;border-radius:2px;
  box-shadow:var(--shadow),inset 0 0 40px rgba(180,160,120,.06);
}
.p{
  background:var(--paper-2);padding:9px 10px 10px;display:flex;flex-direction:column;
  min-height:174px;overflow:hidden;
}
.p-h{
  display:flex;justify-content:space-between;align-items:baseline;gap:6px;
  border-bottom:1px dotted var(--line);padding-bottom:5px;margin-bottom:7px;
}
.p-name{font-size:15px;font-weight:600;letter-spacing:.1em;white-space:nowrap;}
.p-name.ming{color:var(--red);}
.p-gan{font-size:12px;color:var(--ink-4);letter-spacing:.08em;}
.stars{display:flex;flex-wrap:wrap;gap:3px 8px;align-content:flex-start;flex:1;}
.st{font-size:14.5px;letter-spacing:.03em;line-height:1.6;}
.st.major{font-weight:600;}
.st.minor{font-size:13px;color:var(--ink-2);}
.st.tiny{font-size:11.5px;color:var(--ink-4);}
.miao{font-size:10px;color:var(--gold);vertical-align:super;margin-left:1px;letter-spacing:0;}
.si{font-weight:700;font-size:11px;padding:0 3px;border-radius:2px;margin-left:2px;line-height:1.6;}
.si.lu{color:var(--green);background:rgba(55,105,63,.1);}
.si.quan{color:var(--purple);background:rgba(99,65,127,.1);}
.si.ke{color:var(--blue);background:rgba(42,96,143,.1);}
.si.ji{color:#fff;background:var(--red);}
.p-foot{
  display:flex;align-items:flex-end;justify-content:space-between;
  gap:6px;flex:none;margin-top:6px;min-height:17px;
}
.p-dx{
  font-size:10.5px;color:var(--ink-3);letter-spacing:.05em;white-space:nowrap;
  background:var(--paper);border:1px solid var(--line-2);border-radius:3px;
  padding:0 5px;line-height:15px;
}
.p-dx.cur{background:var(--red);color:#fff;border-color:var(--red);}
.badge{
  font-size:10.5px;letter-spacing:.08em;white-space:nowrap;color:var(--red);
  border:1px solid var(--red-2);border-radius:3px;padding:0 5px;line-height:15px;
  background:rgba(158,35,24,.05);
}
.center{
  grid-column:2 / 4;grid-row:2 / 4;
  background:linear-gradient(158deg,#fffdf8 0%,#f3ecdd 100%);
  border:1px solid var(--line);padding:18px 20px;
  display:flex;flex-direction:column;justify-content:center;gap:4px;position:relative;
}
.center::before{
  content:"";position:absolute;top:7px;right:7px;bottom:7px;left:7px;
  border:1px solid var(--line-2);border-radius:2px;pointer-events:none;
}
.center h2{
  margin:0 0 9px;font-size:16.5px;letter-spacing:.3em;text-align:center;
  font-weight:600;text-indent:.3em;
}
.center .row{
  display:flex;justify-content:space-between;font-size:13.5px;
  border-bottom:1px dotted var(--line-2);padding:5px 2px;
}
.center .row:last-child{border-bottom:0;}
.center .row span:first-child{color:var(--ink-4);letter-spacing:.08em;}
.center .row span:last-child{font-weight:600;letter-spacing:.04em;}
.center .row.cur span:last-child{color:var(--red);}

/* ---------- 四化条 ---------- */
.sihua{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin-top:18px;}
.sh{
  border:1px solid var(--line-2);border-left:3px solid var(--line);border-radius:3px;
  padding:10px 14px;background:var(--paper-2);
}
.sh b{display:block;font-size:12px;letter-spacing:.16em;margin-bottom:3px;}
.sh.lu{border-left-color:var(--green);}   .sh.lu b{color:var(--green);}
.sh.quan{border-left-color:var(--purple);}.sh.quan b{color:var(--purple);}
.sh.ke{border-left-color:var(--blue);}    .sh.ke b{color:var(--blue);}
.sh.ji{border-left-color:var(--red);}     .sh.ji b{color:var(--red);}
.sh p{margin:0;font-size:13.5px;color:var(--ink-2);}

/* ---------- 卡片 / 判读 ---------- */
.card{
  background:var(--paper-2);border:1px solid var(--line-2);border-radius:4px;
  padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 2px rgba(60,45,25,.035);
}
.card h3{
  font-size:15.5px;margin:0 0 11px;letter-spacing:.1em;font-weight:600;
  display:flex;align-items:baseline;gap:9px;line-height:1.6;
}
.card h3 .n{
  font-size:11.5px;color:#fff;background:var(--ink-2);border-radius:2px;
  padding:1px 8px;letter-spacing:.08em;font-weight:400;flex:none;
}
.card p{margin:0 0 10px;}
.card p:last-child{margin-bottom:0;}
.card ul,.card ol{margin:8px 0 10px;padding-left:22px;}
.card li{margin-bottom:5px;}
.q{
  color:var(--ink-2);background:rgba(168,128,31,.07);
  border-left:3px solid var(--gold-2);border-radius:0 3px 3px 0;
  padding:9px 14px;margin:11px 0;font-size:13.5px;line-height:1.85;
}
.q::before{content:"《全书》";color:var(--gold);font-size:11.5px;letter-spacing:.1em;margin-right:6px;}
.hl{color:var(--red);font-weight:600;}
.hl-g{color:var(--green);font-weight:600;}
.tag{
  display:inline-block;font-size:11.5px;padding:1px 8px;border-radius:2px;
  letter-spacing:.06em;margin-right:6px;vertical-align:1px;
}
.tag.pos{background:rgba(55,105,63,.11);color:var(--green);border:1px solid rgba(55,105,63,.26);}
.tag.neg{background:rgba(158,35,24,.08);color:var(--red);border:1px solid rgba(158,35,24,.24);}
.tag.mid{background:rgba(42,96,143,.09);color:var(--blue);border:1px solid rgba(42,96,143,.24);}
.empty{
  color:var(--ink-4);font-size:13px;font-style:normal;
  border:1px dashed var(--line);border-radius:3px;padding:9px 14px;
  background:rgba(214,202,179,.12);
}

/* ---------- 表格 ---------- */
table{width:100%;border-collapse:collapse;font-size:13.5px;margin:12px 0;}
th,td{border:1px solid var(--line-2);padding:8px 12px;text-align:left;vertical-align:top;line-height:1.72;}
th{background:rgba(168,128,31,.08);font-weight:600;letter-spacing:.08em;font-size:12.5px;color:var(--ink-2);}
tr:nth-child(even) td{background:rgba(214,202,179,.1);}
td.dx-cur{background:rgba(158,35,24,.07) !important;font-weight:600;color:var(--red);}
td.g{color:var(--green);} td.r{color:var(--red);}

/* ---------- 结论 ---------- */
.verdict{
  background:linear-gradient(150deg,rgba(158,35,24,.05),rgba(168,128,31,.05));
  border:1px solid rgba(158,35,24,.18);border-radius:4px;padding:19px 24px;margin-bottom:16px;
}
.verdict h3{color:var(--red);}
.warn{color:var(--red-2);font-size:13.5px;}
footer{
  margin-top:38px;padding-top:18px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--ink-4);text-align:center;line-height:2.05;
}

/* ---------- 窄屏 ---------- */
@media (max-width:880px){
  body{padding:20px 10px 48px;font-size:14px;}
  h1{font-size:23px;letter-spacing:.22em;text-indent:.22em;}
  .meta{grid-template-columns:repeat(auto-fit,minmax(145px,1fr));margin-bottom:26px;}
  .chart{grid-template-columns:repeat(2,1fr);grid-template-rows:none;}
  .center{grid-column:1 / 3;grid-row:auto;order:-1;min-height:auto;padding:15px 17px;}
  .p{min-height:auto;}
  .card,.verdict{padding:16px 17px;}
  .sec-title{font-size:17px;margin:30px 0 14px;}
}

/* ---------- 打印 / 导出 PDF ---------- */
@media print{
  @page{margin:14mm 12mm;}
  body{background:#fff !important;padding:0;font-size:10.5pt;line-height:1.7;color:#000;}
  .wrap{max-width:none;}
  header{padding-bottom:12px;margin-bottom:16px;}
  h1{font-size:21pt;}
  .meta{margin-bottom:16px;}
  .chart{box-shadow:none;border:1.5px solid #000;gap:.5px;padding:.5px;background:#000;}
  .p{min-height:auto;background:#fff;}
  .center{background:#fff;} .center::before{display:none;}
  .card,.verdict,.sh{box-shadow:none;border-color:#b9b1a4;}
  .card,.verdict,.sh,.q,tr,li{break-inside:avoid;page-break-inside:avoid;}
  .verdict,.q{background:#fafafa !important;}
  .sec-title{break-after:avoid;page-break-after:avoid;}
  .card{padding:12px 14px;margin-bottom:10px;}
  footer{margin-top:16px;}
}
"""


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _star_cls(name, major):
    if major:
        return "st major"
    if name in _LUCKY_OR_SHA:
        return "st minor"
    return "st tiny"


# 辅佐煞化诸星（用于分档渲染）
_LUCKY_OR_SHA = {
    "左辅", "右弼", "文昌", "文曲", "天魁", "天钺", "禄存", "天马",
    "擎羊", "陀罗", "火星", "铃星", "地空", "地劫",
    "天刑", "天姚", "红鸾", "天喜", "三台", "八座", "恩光", "天贵",
    "台辅", "凤阁", "龙池", "天虚", "天哭", "天福", "天官", "天厨",
    "咸池", "寡宿", "孤辰", "蜚廉", "破碎", "华盖", "天伤", "天使",
    "截空", "旬空", "天贵", "天才", "天寿", "封诰", "天巫", "阴煞",
    "解神", "天月", "大耗", "小耗", "官符", "贯索", "丧门", "白虎",
    "吊客", "病符", "岁建", "晦气", "飞廉",
}


def _render_stars(stars, major_names):
    """星曜渲染。stars 为 [(name, brightness, mutagen), ...]"""
    if not stars:
        return '<span class="st tiny">（空宫）</span>'
    out = []
    # 主星优先，其余按原序
    ordered = ([s for s in stars if s[0] in major_names]
               + [s for s in stars if s[0] not in major_names])
    for name, b, m in ordered:
        is_major = name in major_names
        cls = _star_cls(name, is_major)
        html = '<span class="%s">%s' % (cls, esc(name))
        if b:
            html += '<sup class="miao">%s</sup>' % esc(b)
        if m:
            html += '<span class="si %s">%s</span>' % (
                MUTAGEN_CLS.get(m, "ke"), esc(m))
        html += "</span>"
        out.append(html)
    return "".join(out)


def _md_inline(s):
    """极简行内 markdown：**粗体**、*斜体*、`代码`、[[高亮]]、[[绿:...]]"""
    s = esc(s)
    s = re.sub(r"\[\[g:(.+?)\]\]", r'<span class="hl-g">\1</span>', s)
    s = re.sub(r"\[\[(.+?)\]\]", r'<span class="hl">\1</span>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def md_to_html(md):
    """把判读 markdown 转成 HTML 片段（段落 / 无序列表 / 有序列表 / 引用）。"""
    if not md or not md.strip():
        return ""
    lines = md.replace("\r\n", "\n").split("\n")
    html, buf, mode = [], [], None       # mode: 'ul' | 'ol' | 'p' | 'q'

    def flush():
        nonlocal buf, mode
        if not buf:
            mode = None
            return
        if mode == "ul":
            html.append("<ul>" + "".join("<li>%s</li>" % _md_inline(x)
                                         for x in buf) + "</ul>")
        elif mode == "ol":
            html.append("<ol>" + "".join("<li>%s</li>" % _md_inline(x)
                                         for x in buf) + "</ol>")
        elif mode == "q":
            html.append('<div class="q">%s</div>'
                        % "<br>".join(_md_inline(x) for x in buf))
        else:
            html.append("<p>%s</p>" % "<br>".join(_md_inline(x) for x in buf))
        buf, mode = [], None

    for raw in lines:
        ln = raw.rstrip()
        s = ln.strip()
        if not s:
            flush()
            continue
        mu, mo = re.match(r"^[-*+]\s+(.*)$", s), re.match(r"^\d+[.)]\s+(.*)$", s)
        mq = re.match(r"^>\s?(.*)$", s)
        if mu:
            if mode != "ul":
                flush()
            mode, buf = "ul", buf + [mu.group(1)]
        elif mo:
            if mode != "ol":
                flush()
            mode, buf = "ol", buf + [mo.group(1)]
        elif mq:
            if mode != "q":
                flush()
            mode, buf = "q", buf + [mq.group(1)]
        else:
            if mode in ("ul", "ol", "q"):
                flush()
            mode = mode or "p"
            buf.append(s)
    flush()
    return "\n".join(html)


def parse_interpret(text):
    """解析判读文件。

    约定：用 `## 标题` 分节；标题可写槽位键（ming_shen）或中文标题
    （一、命身与格局）。返回 {slot_key: markdown}
    """
    if not text:
        return {}
    title_to_key = {}
    for key, title, _ in SLOTS:
        title_to_key[key] = key
        title_to_key[title] = key
        title_to_key[title.split("、", 1)[-1]] = key   # 允许省略序号

    out, cur, buf = {}, None, []
    for raw in text.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^##\s+(.+?)\s*$", raw)
        if m:
            if cur:
                out[cur] = "\n".join(buf).strip()
            head = m.group(1).strip()
            cur = title_to_key.get(head)
            if cur is None:          # 模糊匹配
                for k, t, _ in SLOTS:
                    if k in head or t.split("、", 1)[-1] in head:
                        cur = k
                        break
            buf = []
            continue
        if cur:
            buf.append(raw)
    if cur:
        out[cur] = "\n".join(buf).strip()
    return out


# ---------------------------------------------------------------------------
# 主渲染
# ---------------------------------------------------------------------------

def render_html(r, interpret=None, gen_note=None):
    """把 build() 的结果渲染为完整 HTML 字符串。

    interpret: {slot_key: markdown}，由 parse_interpret() 产出，可为 None
    """
    from ziwei_pan import (JU_NAME, MAJOR_STARS, SOUL_STAR, BODY_STAR,
                           ZHI_TABOO, NAYIN_TABOO, nayin_of, palace_label,
                           format_lunar, XIAOXIAN_START, GAN)

    interpret = interpret or {}
    info, meta = r["info"], r["meta"]
    ly, lm, ld, leap = info["lunar"]
    si = info.get("solar_input", info["solar_date"])

    title = "紫微斗数命盘 · %s年%s月%s · %s时 · %s命" % (
        info["year_gan"] + info["year_zhi"], format_lunar_month(lm),
        format_lunar_num(ld), info["hour_zhi"], r["sex"])

    H = []
    A = H.append
    A('<!DOCTYPE html>')
    A('<html lang="zh-CN">')
    A('<head>')
    A('<meta charset="UTF-8">')
    A('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    A("<title>%s</title>" % esc(title))
    A("<style>%s</style>" % CSS.strip())
    A("</head>")
    A("<body><div class=\"wrap\">")

    # ---------- 头部 ----------
    A("<header>")
    A("<h1>紫微斗数命盘</h1>")
    clock = ("%02d:%02d（%s时）" % (info["hour"], info["minute"], info["hour_zhi"])
             if info["clock_known"] else "%s时（时刻未知）" % info["hour_zhi"])
    A('<div class="sub">%s年%s月%s · %s · %s</div>' % (
        info["year_gan"] + info["year_zhi"],
        format_lunar_month(lm), format_lunar_num(ld), clock, esc(r["sex"]) + "命"))
    A('<div class="seal">%s · %s · 命主%s</div>' % (
        esc(JU_NAME[meta["ju"]]),
        "%s%s命" % (meta["ming_gan"], info["ming_zhi"]),
        esc(SOUL_STAR[info["ming_zhi"]])))
    A("</header>")

    # ---------- 基本信息 ----------
    A('<div class="meta">')
    for label, val in (
        ("阳历", "%04d-%02d-%02d%s" % (si.year, si.month, si.day,
                                       "" if not info["clock_known"]
                                       else " %02d:%02d" % (info["hour"], info["minute"]))),
        ("农历", format_lunar(ly, lm, ld, leap)),
        ("时辰", info["hour_zhi"]),
        ("性别", r["sex"]),
        ("出生地", r.get("place") or "—"),
        ("生年干支", info["year_gan"] + info["year_zhi"]),
        ("命宫", meta["ming_gan"] + info["ming_zhi"]),
        ("身宫", info["shen_zhi"]),
        ("五行局", JU_NAME[meta["ju"]]),
        ("命主 / 身主", "%s / %s" % (SOUL_STAR[info["ming_zhi"]],
                                    BODY_STAR[info["year_zhi"]])),
        ("命宫纳音", "%s" % (nayin_of(meta["ming_gan"], info["ming_zhi"])[0])),
        ("断事年份", "%d 年（虚岁 %d）" % (r["current_year"], r["age"])),
    ):
        A("<div><span>%s</span><b>%s</b></div>" % (esc(label), esc(val)))
    A("</div>")

    # ---------- 命盘 ----------
    A('<div class="sec-title">十二宫盘</div>')
    A('<div class="chart">')

    # 大限岁数映射（地支 -> 岁数区间）
    dx_of_zhi = {}
    dx_rows = (r["yun"]["daxian"] if r["daxian_convention"] == "quanshu"
               else r["yun"]["daxian_common"])
    for row in dx_rows:
        dx_of_zhi[row["zhi"]] = row["range"]
    cur_dx_zhi = r["cur_daxian"]["zhi"] if r.get("cur_daxian") else None

    for p in r["palaces"]:
        zhi = p["zhi"]
        if zhi not in ZHI_GRID:
            continue
        row, col = ZHI_GRID[zhi]
        is_ming = zhi == info["ming_zhi"]
        is_shen = zhi == info["shen_zhi"]
        A('<div class="p" style="grid-area:%d/%d/%d/%d;">'
          % (row, col, row + 1, col + 1))
        A('<div class="p-h">')
        nm = palace_label(p["name"])
        A('<span class="p-name%s">%s</span>'
          % (" ming" if is_ming else "", esc(nm)))
        A('<span class="p-gan">%s%s</span>' % (esc(p["gan"]), esc(zhi)))
        A("</div>")
        A('<div class="stars">%s</div>' % _render_stars(p["stars"], MAJOR_STARS))
        # 底栏：大限岁数 + 角标
        foot = []
        if zhi in dx_of_zhi:
            lo, hi = dx_of_zhi[zhi]
            cur = " cur" if zhi == cur_dx_zhi else ""
            foot.append('<span class="p-dx%s">%d–%d</span>' % (cur, lo, hi))
        if is_ming or is_shen:
            mark = "命宫◆身宫" if (is_ming and is_shen) else ("命宫" if is_ming else "身宫")
            foot.append('<span class="badge">%s</span>' % mark)
        A('<div class="p-foot">%s</div>' % "".join(foot))
        A("</div>")

    # 中宫
    A('<div class="center">')
    A("<h2>紫微斗数</h2>")
    A('<div class="row"><span>生年</span><span>%s%s</span></div>'
      % (esc(info["year_gan"]), esc(info["year_zhi"])))
    A('<div class="row"><span>命宫</span><span>%s%s</span></div>'
      % (esc(meta["ming_gan"]), esc(info["ming_zhi"])))
    A('<div class="row"><span>身宫</span><span>%s</span></div>' % esc(info["shen_zhi"]))
    A('<div class="row"><span>五行局</span><span>%s</span></div>' % esc(JU_NAME[meta["ju"]]))
    A('<div class="row"><span>命主</span><span>%s</span></div>'
      % esc(SOUL_STAR[info["ming_zhi"]]))
    A('<div class="row"><span>身主</span><span>%s</span></div>'
      % esc(BODY_STAR[info["year_zhi"]]))
    A('<div class="row"><span>紫微</span><span>%s</span></div>' % esc(meta["ziwei_zhi"]))
    A('<div class="row"><span>天府</span><span>%s</span></div>' % esc(meta["tianfu_zhi"]))
    if r.get("current_gz"):
        A('<div class="row cur"><span>流年</span><span>%s（虚岁%d）</span></div>'
          % (esc(r["current_gz"]), r["age"]))
    A("</div>")
    A("</div>")     # .chart

    # ---------- 四化 ----------
    lx, qx, kx, jx = meta["mutagen"]
    A('<div class="sec-title">四化（生年干 %s）</div>' % esc(info["year_gan"]))
    A('<div class="sihua">')
    for key, star in zip(("禄", "权", "科", "忌"), (lx, qx, kx, jx)):
        where = [palace_label(p["name"]) for p in r["palaces"]
                 if any(s[0] == star for s in p["stars"])]
        A('<div class="sh %s"><b>%s · %s</b><p>%s</p></div>'
          % (MUTAGEN_CLS[key], esc(MUTAGEN_CN[key]), esc(star),
             esc("、".join(where) or "不在盘上")))
    A("</div>")

    # ---------- 大限 ----------
    conv = ("《全书》口径：阳男阴女自父母宫顺行 / 阴男阳女自兄弟宫逆行"
            if r["daxian_convention"] == "quanshu" else "通行口径：自命宫起")
    A('<div class="sec-title">大限（%s）</div>' % esc(conv))
    A("<table><tr><th>岁数</th><th>宫位</th><th>地支</th><th>宫干支</th></tr>")
    for row in dx_rows:
        lo, hi = row["range"]
        is_cur = (cur_dx_zhi == row["zhi"]
                  and r.get("cur_daxian")
                  and row["range"] == tuple(r["cur_daxian"]["range"]))
        tds = ["%d–%d%s" % (lo, hi, " ← 当前" if is_cur else ""),
               palace_label(row["palace"]), row["zhi"]]
        pobj = next((p for p in r["palaces"] if p["zhi"] == row["zhi"]), None)
        tds.append(pobj["gan"] + pobj["zhi"] if pobj else "—")
        A("<tr>%s</tr>" % "".join(
            '<td class="%s">%s</td>' % ("dx-cur" if is_cur else "", esc(t))
            for t in tds))
    A("</table>")

    # ---------- 小限 ----------
    A('<div class="sec-title">小限（不论阴阳，男顺女逆；生年支 %s 起 %s）</div>'
      % (esc(info["year_zhi"]), esc(XIAOXIAN_START[info["year_zhi"]])))
    A("<table><tr><th>地支</th><th>宫位</th><th>岁数</th></tr>")
    for row in r["yun"]["xiaoxian"]:
        is_cur = r["age"] in row["ages"]
        A("<tr>%s</tr>" % "".join(
            '<td class="%s">%s</td>' % ("dx-cur" if is_cur else "", esc(t))
            for t in (row["zhi"], palace_label(row["palace"]),
                      "、".join(str(a) for a in row["ages"])
                      + (" ← 当前" if is_cur else ""))))
    A("</table>")

    # ---------- 童限 ----------
    A('<div class="sec-title">童限（起大限前之过渡）</div>')
    A('<div class="card"><p>%s</p></div>'
      % "；".join("%d 岁 %s" % (t["age"], esc(t["palace"]))
                  for t in r["yun"]["tonglian"]))

    # ---------- 当前运限 ----------
    A('<div class="sec-title">当前运限</div>')
    A('<div class="card">')
    A("<p><b>%d 年（%s），虚岁 %d</b></p>"
      % (r["current_year"], esc(r["current_gz"]), r["age"]))
    if r.get("cur_daxian"):
        lo, hi = r["cur_daxian"]["range"]
        A("<p>大限：%d–%d 岁 行 <b>%s</b>（%s）</p>"
          % (lo, hi, esc(r["cur_daxian"]["zhi"]),
             esc(palace_label(r["cur_daxian"]["palace"]))))
    if r.get("cur_xiaoxian"):
        A("<p>小限：行 <b>%s</b>（%s）</p>"
          % (esc(r["cur_xiaoxian"]["zhi"]),
             esc(palace_label(r["cur_xiaoxian"]["palace"]))))
    is_yang = GAN.index(info["year_gan"]) % 2 == 0
    is_male = r["sex"] == "男"
    dou = "南斗" if ((is_yang and is_male) or (not is_yang and not is_male)) else "北斗"
    span = ("大限断下五年、小限断下半年" if dou == "南斗"
            else "大限断上五年、小限断上半年")
    A("<p>南北斗应期：<b>%s为福</b>（%s）</p>" % (dou, span))
    A("<p>十二支所忌：%s</p>" % esc(ZHI_TABOO[info["year_zhi"]]))
    nn, wx = nayin_of(meta["ming_gan"], info["ming_zhi"])
    gua, zhis = NAYIN_TABOO[wx]
    A('<p class="warn">纳音忌宫：命宫纳音「%s」属%s，忌 %s（%s）——'
      '「纵然吉曜相逢照，未免官灾闹一场」</p>'
      % (esc(nn), esc(wx), esc(gua), esc(zhis)))
    ming_major = r.get("ming_stars") or []
    if ming_major:
        from ziwei_pan import SOLVE_JIAXIAN
        solve = [s for s in ming_major if s in SOLVE_JIAXIAN]
        A("<p>解灾检查：命宫主星 %s%s</p>"
          % (esc("、".join(ming_major)),
             "（<b>%s</b> 在命，可解羊陀夹限）" % esc("、".join(solve))
             if solve else "（不在解灾四星内，逢夹限须谨慎）"))
    A("</div>")

    # ---------- 判读 ----------
    A('<div class="sec-title">判读</div>')
    for key, ttl, hint in SLOTS:
        body = interpret.get(key, "").strip()
        A('<div class="card">')
        A('<h3><span class="n">%s</span>%s</h3>'
          % (esc(ttl.split("、")[0]), esc(ttl.split("、", 1)[-1])))
        if body:
            A(md_to_html(body))
        else:
            A('<div class="empty">（本节点未提供判读。可另用 --interpret 传入撰写好的'
              '判读 markdown；提示：%s）</div>' % esc(hint))
        A("</div>")

    # ---------- 警告 ----------
    if r.get("warnings"):
        A('<div class="sec-title">历法提示</div>')
        A('<div class="card">')
        seen = set()
        for w in r["warnings"]:
            if w in seen:
                continue
            seen.add(w)
            A('<p class="warn">· %s</p>' % esc(w))
        A("</div>")

    # ---------- 页脚 ----------
    A("<footer>")
    A("依明刊本《紫微斗数全书》（托名宋·陈抟，明·罗洪先序，嘉靖庚戌 1550）安星诀排布<br>")
    A("排盘由 <b>ziwei_pan.py</b> 计算，结果可复现；判读部分仅供传统文化研习参考<br>")
    if gen_note:
        A("%s<br>" % esc(gen_note))
    A("本页不构成任何决策依据")
    A("</footer>")

    A("</div></body></html>")
    return "\n".join(H)


_CN_NUM = "〇一二三四五六七八九十"


def format_lunar_month(n):
    """农历月的写法：正月 / 六月 / 十月 / 冬月 / 腊月。"""
    if n <= 0:
        return str(n)
    if n == 1:
        return "正"
    if n == 11:
        return "冬"
    if n == 12:
        return "腊"
    if n <= 10:
        return _CN_NUM[n]
    return str(n)


def format_lunar_num(n):
    """农历**日**的中文写法：初一 / 初十 / 十五 / 二十 / 廿一 / 三十。

    注意与月不同——日必须冠「初/廿/三」，如 1 日作「初一」而非「一」。
    若仅写作「一」，会与月份写法混淆（六月一日 → 「六月一」）。
    """
    if n <= 0:
        return str(n)
    if n <= 10:
        return "初" + (_CN_NUM[n] if n < 10 else "十")
    if n < 20:
        return "十" + _CN_NUM[n - 10]
    if n == 20:
        return "二十"
    if n < 30:
        return "廿" + _CN_NUM[n - 20]
    return "三十"
