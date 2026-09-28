#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""紫微斗数 HTML 渲染器回归测试（零依赖，不联网、不调浏览器）。

覆盖：
  1. 结构完整性    —— 4×4 宫格、十二宫齐全、中宫九行、必需区块
  2. 格位正确性    —— 每宫 grid-area 与 _BOOK_GRID 传统方位表一致
  3. 星曜渲染      —— 主星/辅佐/杂曜分级、庙陷 sup、四化标记
  4. 判读槽位      —— parse_interpret 解析、注入、未给槽位留占位
  5. md → HTML    —— 段落 / 无序表 / 有序表 / 引用 / 行内标记 / 转义
  6. 确定性与安全  —— 同输入同输出、无外部资源、无未转义注入
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ziwei_pan as zp          # noqa: E402
import ziwei_html as zh         # noqa: E402

FAILS = []
CHECKS = [0]


def check(label, got, want):
    CHECKS[0] += 1
    if got != want:
        FAILS.append("%s\n    期望 %r\n    实得 %r" % (label, want, got))


def ok(label, cond, detail=""):
    CHECKS[0] += 1
    if not cond:
        FAILS.append("%s\n    %s" % (label, detail or "条件不成立"))


# 传统方位（明刊本 4×4：巳午未申 顶行；辰/酉 两侧；卯/戌 两侧；寅丑子亥 底行）
BOOK_GRID = {
    "巳": (1, 1), "午": (1, 2), "未": (1, 3), "申": (1, 4),
    "辰": (2, 1), "酉": (2, 4), "卯": (3, 1), "戌": (3, 4),
    "寅": (4, 1), "丑": (4, 2), "子": (4, 3), "亥": (4, 4),
}

BASE = dict(solar="1994-07-28", hour=12, minute=0, shichen=None, sex="男",
            place=None, leap_policy="next-month", late_zishi="next-day",
            daxian_convention="quanshu", year_divide="exact",
            target_year=2026, deceased_year=None)


def build(**over):
    kw = dict(BASE)
    kw.update(over)
    from datetime import date
    return zp.build(date(1994, 7, 28), **{k: v for k, v in kw.items()
                                          if k != "solar"})


# ---------------------------------------------------------------------------
# 1. 结构完整性
# ---------------------------------------------------------------------------

def test_structure():
    r = build()
    h = zh.render_html(r)
    ok("渲染结果非空", len(h) > 5000, "长度 %d" % len(h))
    ok("是完整 HTML 文档", h.lstrip().startswith("<!DOCTYPE html>"))
    ok("有 lang=zh-CN", '<html lang="zh-CN">' in h)
    ok("UTF-8 声明", '<meta charset="UTF-8">' in h)
    ok("有 viewport", 'name="viewport"' in h)
    ok("有标题", "<title>" in h and "</title>" in h)
    ok("闭合标签完整", h.rstrip().endswith("</html>"))

    ok("宫格 .p 恰好 12 个", h.count('<div class="p"') == 12,
       "实得 %d" % h.count('<div class="p"'))
    ok("宫头 .p-h 12 个", h.count('class="p-h"') == 12)
    ok("星曜区 .stars 12 个", h.count('class="stars"') == 12)
    ok("底栏 .p-foot 12 个", h.count('class="p-foot"') == 12)
    ok("有中宫 .center", 'class="center"' in h)
    # 中宫固定 8 行（生年/命宫/身宫/五行局/命主/身主/紫微/天府）+ 有流年时 1 行
    n_row = h.count('<div class="row">') + h.count('<div class="row cur">')
    ok("中宫 8–9 行", n_row in (8, 9), "实得 %d" % n_row)
    ok("中宫含命宫行", "<span>命宫</span>" in h)
    ok("中宫含五行局行", "<span>五行局</span>" in h)
    ok("有大限表", h.count('class="card"') >= 5)
    ok("有打印样式", "@media print" in h)
    ok("有响应式断点", "@media" in h and "880px" in h)


# ---------------------------------------------------------------------------
# 2. 格位正确性
# ---------------------------------------------------------------------------

def test_grid_placement():
    r = build()
    h = zh.render_html(r)
    blocks = re.split(r'<div class="p"', h)[1:]
    ok("解析到 12 宫块", len(blocks) == 12, "实得 %d" % len(blocks))
    seen = set()
    for blk in blocks:
        m = re.search(r'grid-area:(\d+)/(\d+)/(\d+)/(\d+);', blk)
        ok("宫块含 grid-area", bool(m), blk[:120])
        if not m:
            continue
        row, col, r2, c2 = (int(x) for x in m.groups())
        ok("grid-area 跨 1 格", (r2 - row, c2 - col) == (1, 1),
           "row%d-%d col%d-%d" % (row, r2, col, c2))
        gz = re.search(r'class="p-gan"[^>]*>([\u4e00-\u9fff])([\u4e00-\u9fff])<', blk)
        ok("宫块含干支", bool(gz), blk[:120])
        if gz:
            zhi = gz.group(2)
            want = BOOK_GRID.get(zhi)
            ok("方位正确 %s" % zhi, (row, col) == want,
               "%s 期望 %s 实得 (%d,%d)" % (zhi, want, row, col))
            ok("方位无重复 %s" % zhi, zhi not in seen, "重复出现")
            seen.add(zhi)
    ok("十二地支齐全", seen == set(BOOK_GRID), "缺 %s" % (set(BOOK_GRID) - seen))


# ---------------------------------------------------------------------------
# 3. 星曜渲染
# ---------------------------------------------------------------------------

def test_star_rendering():
    r = build()
    h = zh.render_html(r)
    ok("有主星样式 st major", 'class="st major"' in h)
    ok("有辅佐样式 st minor", 'class="st minor"' in h)
    ok("有杂曜样式 st tiny", 'class="st tiny"' in h)
    ok("庙陷用 sup.miao", 'class="miao">' in h)
    ok("四化标记 .si 存在", 'class="si ' in h)

    # 四化恰好 4 颗，且四色齐全
    four = re.findall(r'class="si (lu|quan|ke|ji)"', h)
    ok("四化标记共 4 处", len(four) == 4, "实得 %d" % len(four))
    ok("四色齐全", set(four) == {"lu", "quan", "ke", "ji"}, repr(sorted(four)))
    # 甲年：廉贞化禄、破军化权、武曲化科、太阳化忌
    r2 = build()
    ok("甲年四化为廉破武阳",
       tuple(r2["meta"]["mutagen"]) == ("廉贞", "破军", "武曲", "太阳"),
       repr(r2["meta"]["mutagen"]))
    # 四化字符须紧跟所在的星名 span 内
    for star, label, ch in (("廉贞", "lu", "禄"), ("破军", "quan", "权"),
                            ("武曲", "ke", "科"), ("太阳", "ji", "忌")):
        pat = r'>(%s)(?:<sup[^>]*>[^<]*</sup>)?<span class="si %s">%s</span>' % (
            star, label, ch)
        ok("四化归属 %s→%s" % (star, ch),
           len(re.findall(pat, h)) == 1,
           "匹配 %d 次" % len(re.findall(pat, h)))

    # 主星应在同一宫中排在辅佐星之前
    blk = re.split(r'<div class="p"', h)[1]
    i = blk.find("</div>")            # 星曜区
    seg = blk[blk.find('class="stars"'):]
    idx_major = seg.find('class="st major"')
    idx_minor = seg.find('class="st minor"')
    if idx_major >= 0 and idx_minor >= 0:
        ok("主星排在辅佐之前", idx_major < idx_minor)

    # 转义：星名不会被当标签
    ok("无 <script> 注入", "<script" not in h)
    ok("星曜区无裸标签", re.search(
        r'class="st [^"]*"[^>]*>[^<]*<(?!/span|sup)[a-z]', h) is None)
    ok("星曜 span 数 > 0", h.count('class="st ') > 0)


# ---------------------------------------------------------------------------
# 4. 判读槽位
# ---------------------------------------------------------------------------

def test_slots():
    text = (
        "# 判读\n"
        "一、命身与格局\n"   # 无 ## → 不识别
        "## 一、命身与格局\n命宫**丁丑**，紫微不在命。\n"
        "## 二、四化与生克\n- 廉贞化禄\n- 太阳化忌\n"
        "## 三、十二宫分述\n1. 命宫：天魁陀罗\n2. 财帛：天相\n"
        "## 四、运限推演\n> 大限行至巳宫\n"
        "## 五、综合论断\n总评：宜稳。\n"
        "## 无关章节\n这段应被忽略。\n"
    )
    d = zh.parse_interpret(text)
    for key, _, _ in zh.SLOTS:
        ok("槽位 %s 已解析" % key, key in d, "实际键 %s" % sorted(d))
    ok("无关章节被丢弃", "这段应被忽略" not in "".join(d.values()))
    ok("命身槽位内容正确", "紫微不在命" in d.get("ming_shen", ""))

    # 槽位键也可直接用
    d2 = zh.parse_interpret("## ming_shen\n直接写键。\n")
    ok("支持直接写槽位键", d2.get("ming_shen") == "直接写键。")

    # 省略序号也可
    d3 = zh.parse_interpret("## 命身与格局\n省略序号。\n")
    ok("支持省略序号", d3.get("ming_shen") == "省略序号。", repr(d3))

    r = build()
    h_full = zh.render_html(r, interpret=d)
    for _key, ttl, _hint in zh.SLOTS:
        seq, nm = ttl.split("、", 1)
        ok("页面含槽位标题 %s" % ttl,
           ('<span class="n">%s</span>%s</h3>' % (seq, nm)) in h_full,
           "未找到 %s" % ttl)
    ok("注入内容出现在页面", "宜稳" in h_full)
    ok("注入的粗体已转 b", "<b>丁丑</b>" in h_full)
    ok("注入的无序表已转 ul", "<ul>" in h_full)
    ok("注入的有序表已转 ol", "<ol>" in h_full)
    ok("注入的引用已转 .q", 'class="q"' in h_full)

    # 未注入时留占位
    h_empty = zh.render_html(r)
    ok("无判读时有占位 .empty", 'class="empty"' in h_empty)
    ok("无判读时不含注入内容", "宜稳" not in h_empty)
    ok("未注入槽位数 = 5", h_empty.count('class="empty"') == 5,
       "实得 %d" % h_empty.count('class="empty"'))

    # 部分注入：只填两个，其余仍占位
    part = zh.render_html(r, interpret={"ming_shen": "只填了这一段。"})
    ok("部分注入保留 4 个占位", part.count('class="empty"') == 4,
       "实得 %d" % part.count('class="empty"'))
    ok("部分注入内容在页面", "只填了这一段" in part)


# ---------------------------------------------------------------------------
# 5. md → HTML
# ---------------------------------------------------------------------------

def test_md_to_html():
    md = ("普通段落第一行\n第二行\n\n"
          "- 项一\n- 项二\n\n"
          "1. 甲\n2. 乙\n\n"
          "> 原书判词\n> 第二行\n\n"
          "带 **粗体** 与 `代码` 与 [[高亮]] 与 [[g:绿]].\n")
    h = zh.md_to_html(md)
    ok("段落成 p", h.startswith("<p>"))
    ok("换行成 br", "<br>" in h)
    ok("无序表成 ul/li", "<ul>" in h and h.count("<li>") >= 2)
    ok("有序表成 ol", "<ol>" in h)
    ok("引用成 .q", '<div class="q">' in h)
    ok("** 成 b", "<b>粗体</b>" in h)
    ok("` 成 code", "<code>代码</code>" in h)
    ok("[[]] 成 hl", '<span class="hl">高亮</span>' in h)
    ok("[[g:]] 成 hl-g", '<span class="hl-g">绿</span>' in h)

    # 边界
    ok("空输入返回空", zh.md_to_html("") == "")
    ok("纯空白返回空", zh.md_to_html("   \n\n  ") == "")

    # 转义优先：HTML 标签必须被转义，不能穿透
    h2 = zh.md_to_html("<script>alert(1)</script> & \"x\"")
    ok("尖括号被转义", "<script>" not in h2 and "&lt;script&gt;" in h2)
    ok("& 被转义", "&amp;" in h2)
    ok("引号被转义", "&quot;" in h2)

    # 行内标记内也要转义
    h3 = zh.md_to_html("**<img src=x onerror=1>**")
    ok("行内标记内尖括号转义", "<img" not in h3 and "&lt;img" in h3)


# ---------------------------------------------------------------------------
# 6. 确定性与安全
# ---------------------------------------------------------------------------

def test_determinism_and_safety():
    r = build()
    a = zh.render_html(r)
    b = zh.render_html(r)
    ok("同输入同输出", a == b)

    r_other = build(sex="女")
    ok("不同命造输出不同", zh.render_html(r_other) != a)

    # 无外部资源（离线可用）
    ok("无外部 http(s) 资源",
       not re.search(r'(src|href)\s*=\s*["\']https?://', a))
    ok("无 <link rel=stylesheet>", "<link" not in a)
    ok("无外部 script", "<script" not in a)
    ok("无 base64 外链图片", "data:image" not in a)
    ok("样式为内联 <style>", "<style>" in a and "</style>" in a)

    # 空盘（无星曜）也要能渲染
    r_empty = build()
    for p in r_empty["palaces"]:
        p["stars"] = []
    h_empty = zh.render_html(r_empty)
    ok("空宫盘可渲染", len(h_empty) > 3000 and '（空宫）' in h_empty)

    # 判读含未闭合花括号不应破坏结构
    h_brace = zh.render_html(r, interpret={"ming_shen": "a } b { c"})
    ok("异常符号不破坏结构", h_brace.count('<div class="p"') == 12)


# ---------------------------------------------------------------------------
# 7. 农历中文数字
# ---------------------------------------------------------------------------

def test_lunar_num():
    """日：农历日必须冠「初」；月：正月/冬月/腊月。"""
    day_cases = [(1, "初一"), (5, "初五"), (10, "初十"), (11, "十一"),
                 (15, "十五"), (19, "十九"), (20, "二十"), (21, "廿一"),
                 (23, "廿三"), (29, "廿九"), (30, "三十")]
    for n, want in day_cases:
        check("农历日 %d" % n, zh.format_lunar_num(n), want)

    month_cases = [(1, "正"), (2, "二"), (6, "六"), (10, "十"),
                   (11, "冬"), (12, "腊")]
    for n, want in month_cases:
        check("农历月 %d" % n, zh.format_lunar_month(n), want)

    # 月份与日不能混用同一函数（1 月 vs 1 日）
    ok("月日写法有别", zh.format_lunar_num(1) == "初一"
       and zh.format_lunar_month(1) == "正")


# ---------------------------------------------------------------------------
# 8. md 文本 与 HTML 命盘一致性（同源不得互相矛盾）
# ---------------------------------------------------------------------------

def test_md_html_parity():
    r = build()
    md = zp.format_report(r)
    h = zh.render_html(r)

    # HTML 逐宫：(干支, {星名})
    panes = {}
    for blk in re.split(r'<div class="p"', h)[1:]:
        g = re.search(r'class="p-gan"[^>]*>([\u4e00-\u9fff]{2})<', blk)
        i = blk.find('class="stars"')
        if not (g and i >= 0):
            continue
        panes[g.group(1)] = set(re.findall(
            r'<span class="st [^"]*"[^>]*>\s*([\u4e00-\u9fff]+)', blk[i:]))

    ok("HTML 有 12 宫干支", len(panes) == 12, "实得 %d" % len(panes))

    # md 十二宫表逐行核对
    sec = md.split("## 十二宫", 1)[1].split("## 四化", 1)[0]
    rows = 0
    for line in sec.splitlines():
        if set(line.strip()) <= set("|-: "):        # 分隔行
            continue
        m = re.match(r"\|\s*[^|]+\|\s*([\u4e00-\u9fff]{2})\s*\|\s*([^|]+)\|", line)
        if not m:
            continue
        gz, cell = m.group(1), m.group(2)
        if gz == "干支":                             # 表头
            continue
        if gz not in panes:
            ok("md 干支 %s 在 HTML 中存在" % gz, False)
            continue
        rows += 1
        missing = {s for s in panes[gz] if s not in cell}
        ok("md/HTML 一致 %s" % gz, not missing,
           "HTML 有而 md 缺: %s" % " ".join(sorted(missing)))
    ok("md 十二宫表有 12 行", rows == 12, "实得 %d" % rows)

    # 四化在两处必须一致
    lx, qx, kx, jx = r["meta"]["mutagen"]
    for star in (lx, qx, kx, jx):
        ok("四化星 %s 在 HTML 中" % star, star in h)
    ok("四化段在 md 中", "化禄" in md or lx in md)

    # 命身局关键字段
    for label, val in (("命宫", r["meta"]["ming_gan"] + r["info"]["ming_zhi"]),
                       ("五行局", zp.JU_NAME[r["meta"]["ju"]])):
        ok("%s 两处一致" % label, val in md and val in h, "val=%s" % val)


# ---------------------------------------------------------------------------
# 9. 文档一致性：README 承诺的断言数必须与实际相符
# ---------------------------------------------------------------------------

def test_readme_assertion_count():
    readme = os.path.join(os.path.dirname(HERE), "README.md")
    if not os.path.exists(readme):
        return
    txt = open(readme, encoding="utf-8").read()
    m = re.search(r"test_ziwei_html\.py\s*#\s*HTML 渲染回归（(\d+) 项断言）", txt)
    ok("README 标注了 HTML 测试断言数", bool(m), "未找到断言数标注")
    if m:
        claimed = int(m.group(1))
        actual = CHECKS[0] + 1        # +1：本条断言自身
        check("README 断言数与实际一致", claimed, actual)


def main():
    print("紫微斗数 HTML 渲染器回归测试")
    print("-" * 56)
    print("1. 结构完整性")
    test_structure()
    print("2. 宫位格位（传统 4×4 方位）")
    test_grid_placement()
    print("3. 星曜渲染（分级 / 庙陷 / 四化）")
    test_star_rendering()
    print("4. 判读槽位（解析 / 注入 / 占位）")
    test_slots()
    print("5. markdown → HTML（含转义）")
    test_md_to_html()
    print("6. 确定性与离线安全")
    test_determinism_and_safety()
    print("7. 农历中文数字")
    test_lunar_num()
    print("8. md 文本 ↔ HTML 命盘一致性")
    test_md_html_parity()
    print("9. 文档一致性（README 断言数）")
    test_readme_assertion_count()
    print("-" * 56)
    print("共 %d 项断言，失败 %d 项" % (CHECKS[0], len(FAILS)))
    for f in FAILS:
        print("  ✗ %s" % f)
    return 1 if FAILS else 0

if __name__ == "__main__":
    sys.exit(main())
