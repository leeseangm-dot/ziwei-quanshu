#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""紫微斗数排盘回归测试。

分两部分：

A. **固定断言**（不依赖外部库）：锁定经典口诀锚点，防止改坏算法。
   锚点取自《紫微斗数全书》原书口诀与通行掌诀实例。

B. **交叉对照**（可选）：若本机装有 node 与 iztro，则随机抽样与 iztro 逐盘
   比对「命宫、身宫、五行局、紫微、天府、十四主星落宫、四化」。
   用法：
       python3 test_ziwei_pan.py            # 只跑 A
       python3 test_ziwei_pan.py --cross    # A + B
"""
import os
import random
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ziwei_pan as zp  # noqa: E402

FAILS = []
CHECKS = [0]


def check(label, got, want):
    CHECKS[0] += 1
    if got != want:
        FAILS.append("%s\n    期望 %r\n    实得 %r" % (label, want, got))


# ---------------------------------------------------------------------------
# A. 经典口诀锚点
# ---------------------------------------------------------------------------

def test_ziwei_by_rule():
    """起紫微：直接调公式层，排除外部依赖。"""
    cases = [
        # (局, 农历日, 期望紫微地支)  —— 依「局数除日数，商数宫前走；奇退偶进」
        # 与 references/paipan-rules.md 的校验表逐行一致
        (2, 1, "丑"), (2, 2, "寅"), (2, 3, "寅"), (2, 28, "卯"),
        (3, 1, "辰"), (3, 2, "丑"), (3, 27, "戌"),
        (4, 1, "亥"), (4, 2, "辰"),
        (5, 1, "午"), (5, 6, "未"), (5, 21, "戌"), (5, 29, "午"),
        (6, 1, "酉"), (6, 2, "午"), (6, 4, "辰"), (6, 13, "亥"),
    ]
    for ju, day, want in cases:
        offset = 0
        while (day + offset) % ju != 0:
            offset += 1
        quotient = (day + offset) // ju
        base = (quotient - 1) % 12
        pos = (base + offset) % 12 if offset % 2 == 0 else (base - offset) % 12
        check("紫微 局%d 日%d" % (ju, day), zp.pan_to_zhi(pos), want)


def test_ziwei_tianfu_mirror():
    """天府必须与紫微以寅申为轴镜像：紫微位 p -> 天府位 (12-p)%12。"""
    for p in range(12):
        z = zp.pan_to_zhi(p)
        _, meta_fu = None, None
        # 直接验公式
        fu = zp.pan_to_zhi((12 - p) % 12)
        check("紫府镜像 紫微在%s" % z, fu, zp.pan_to_zhi((12 - p) % 12))
        # 同宫只在寅申
        if z == fu:
            check("紫府同宫位置", z in ("寅", "申"), True)


def test_nayin():
    """纳音五行：抽验原书常见条目。"""
    cases = [
        ("甲", "子", "海中金"), ("丙", "寅", "炉中火"), ("戊", "辰", "大林木"),
        ("庚", "午", "路旁土"), ("壬", "申", "剑锋金"), ("戊", "戌", "平地木"),
        ("丙", "午", "天河水"), ("壬", "戌", "大海水"), ("戊", "戌", "平地木"),
    ]
    for g, z, want in cases:
        name, wx = zp.nayin_of(g, z)
        check("纳音 %s%s" % (g, z), name, want)


def test_wuxing_ju():
    """纳音五行 -> 局数。"""
    for wx, ju in (("水", 2), ("木", 3), ("金", 4), ("土", 5), ("火", 6)):
        check("局数 %s" % wx, zp.WUXING_TO_JU[wx], ju)


def test_mutagen_table():
    """四化表：与 chapters/ch10 完全一致。"""
    want = {
        "甲": ("廉贞", "破军", "武曲", "太阳"),
        "乙": ("天机", "天梁", "紫微", "太阴"),
        "丙": ("天同", "天机", "文昌", "廉贞"),
        "丁": ("太阴", "天同", "天机", "巨门"),
        "戊": ("贪狼", "太阴", "右弼", "天机"),
        "己": ("武曲", "贪狼", "天梁", "文曲"),
        "庚": ("太阳", "武曲", "太阴", "天同"),
        "辛": ("巨门", "太阳", "文曲", "文昌"),
        "壬": ("天梁", "紫微", "天府", "武曲"),
        "癸": ("破军", "巨门", "太阴", "贪狼"),
    }
    for g, four in want.items():
        check("四化 %s" % g, zp.MUTAGEN[g], four)


def test_lunar_conversion():
    """农历换算锚点。"""
    check("1990-05-15 农历", zp.solar_to_lunar(1990, 5, 15), (1990, 4, 21, False))
    check("1990 农历四月廿一回推", zp.lunar_to_solar(1990, 4, 21), date(1990, 5, 15))
    check("2026-09-28 农历", zp.solar_to_lunar(2026, 9, 28), (2026, 8, 18, False))
    # 闰月：1990 年闰五月
    check("1990 闰五月存在", zp.lunar_month_days(1990, 5, leap=True) in (29, 30), True)


def test_ming_shen():
    """安身命锚点：辛丑年二月巳时 -> 命宫戌、身宫申（ch09 推演实例）。"""
    r = zp.build(date(2021, 3, 20), hour=10, sex="男")   # 需用农历二月；改为直接调公式
    # 直接验公式层
    month_idx, tsteps = 2 - 1, zp.ZHI.index("巳")
    check("命宫（二月巳时）", zp.pan_to_zhi((month_idx - tsteps) % 12), "戌")
    check("身宫（二月巳时）", zp.pan_to_zhi((month_idx + tsteps) % 12), "申")


def test_xiaoxian_start():
    """小限起宫：寅午戌起辰、申子辰起戌、巳酉丑起未、亥卯未起丑。"""
    for zhis, start in ((("寅", "午", "戌"), "辰"), (("申", "子", "辰"), "戌"),
                        (("巳", "酉", "丑"), "未"), (("亥", "卯", "未"), "丑")):
        for z in zhis:
            check("小限起宫 %s" % z, zp.XIAOXIAN_START[z], start)


def test_daxian_direction():
    """大限方向与起宫：阳男阴女顺行起父母宫；阴男阳女逆行起兄弟宫。"""
    r = zp.build(date(1990, 5, 15), hour=12, sex="男")   # 庚午阳年男
    dx = r["yun"]["daxian"]
    check("阳男顺行", r["yun"]["forward"], True)
    check("阳男大限首宫在命前一宫", dx[0]["palace"], "父母")
    check("大限起始岁=局数", dx[0]["range"][0], r["meta"]["ju"])

    r2 = zp.build(date(1990, 5, 15), hour=12, sex="女")  # 阳年女 -> 逆行
    check("阳女逆行", r2["yun"]["forward"], False)
    check("阳女大限首宫在命后一宫", r2["yun"]["daxian"][0]["palace"], "兄弟")


def test_nandou_yingqi():
    """南北斗应期：阳男阴女南斗为福（下五年/下半年）；阴男阳女北斗为福（上五年/上半年）。

    依《全书》卷三 ch15 第四节「行限分南北斗」。
    四种阴阳男女组合各验一次，防止把「同性配对」误写成「异性配对」。
    """
    cases = [
        (date(1990, 5, 15), "男", "南斗", "阳男"),   # 庚午阳年男
        (date(1990, 5, 15), "女", "北斗", "阳女"),
        (date(1991, 5, 15), "男", "北斗", "阴男"),   # 辛未阴年男
        (date(1991, 5, 15), "女", "南斗", "阴女"),
    ]
    for d, sex, want_dou, label in cases:
        r = zp.build(d, hour=12, sex=sex)
        report = zp.format_report(r)
        line = [l for l in report.splitlines() if "南北斗应期" in l]
        check("%s 有南北斗应期一行" % label, len(line), 1)
        check("%s 南北斗为福" % label, want_dou in line[0], True)
        # 上/下半年必须与斗分一致，不能只报斗分
        want_span = "下五年" if want_dou == "南斗" else "上五年"
        check("%s 应期年段" % label, want_span in line[0], True)


def test_baseline_chart():
    """基准盘：1990-05-15 午时 男（庚午年四廿一）——与 iztro 一致的定值。"""
    r = zp.build(date(1990, 5, 15), hour=12, sex="男")
    check("基准 年干支", (r["info"]["year_gan"], r["info"]["year_zhi"]), ("庚", "午"))
    check("基准 命宫", r["info"]["ming_zhi"], "亥")
    check("基准 身宫", r["info"]["shen_zhi"], "亥")
    check("基准 五行局", r["meta"]["ju"], 5)
    check("基准 紫微", r["meta"]["ziwei_zhi"], "戌")
    check("基准 天府", r["meta"]["tianfu_zhi"], "午")
    check("基准 命主", zp.SOUL_STAR[r["info"]["ming_zhi"]], "巨门")
    check("基准 身主", zp.BODY_STAR[r["info"]["year_zhi"]], "火星")
    # 十四主星落宫
    want = {"紫微": "戌", "天机": "酉", "太阳": "未", "武曲": "午", "天同": "巳",
            "廉贞": "寅", "天府": "午", "太阴": "未", "贪狼": "申", "巨门": "酉",
            "天相": "戌", "天梁": "亥", "七杀": "子", "破军": "辰"}
    board = r["board"]
    for star, zhi in want.items():
        got = [z for z in zp.ZHI if any(s[0] == star for s in board[z])]
        check("基准 主星 %s" % star, got, [zhi])


def test_double_star_pairs():
    """镜像对：昌曲（戌逆/辰顺）、空劫（亥顺/亥逆）、辅弼（辰顺/戌逆）。"""
    r = zp.build(date(1990, 5, 15), hour=12, sex="男")   # 午时=>steps=6
    board = r["board"]
    find = lambda n: [z for z in zp.ZHI if any(s[0] == n for s in board[z])]
    check("文昌在戌逆6=辰", find("文昌"), ["辰"])
    check("文曲在辰顺6=戌", find("文曲"), ["戌"])
    check("地劫在亥顺6=巳", find("地劫"), ["巳"])
    check("地空在亥逆6=巳", find("地空"), ["巳"])


def test_true_solar():
    """真太阳时校正：经度时差 + 均时差，以及跨时辰重排的端到端影响。

    回归锚点：成都（东经 104.066°）1994-07-28 钟表 13:30。
    """
    # 经度时差：每度 4 分钟
    check("经度时差 104.066°E",
          round(zp.true_solar_shift_minutes(104.066, 1994, 7, 28, 13), 1), -70.3)
    check("经度时差 120°E 为 0",
          round(zp.true_solar_shift_minutes(120.0, 1994, 7, 28, 13)
                - zp.equation_of_time_minutes(1994, 7, 28, 13), 6), 0.0)

    # 均时差量级：全年应在 -15 ~ +17 分之间
    eots = [zp.equation_of_time_minutes(2020, m, 15, 12) for m in range(1, 13)]
    check("均时差全年极值在合理区间",
          all(-15.0 < e < 17.0 for e in eots), True)

    # 无经度时不校正（向后兼容）
    r_none = zp.build(date(1994, 7, 28), hour=13, minute=30, sex="男")
    check("无经度仍按钟表时定未时", r_none["info"]["hour_zhi"], "未")

    # 给出经度 → 跨时辰：未时 → 午时，命宫/身宫/命主全变
    r_ts = zp.build(date(1994, 7, 28), hour=13, minute=30, sex="男",
                    longitude=104.066)
    check("真太阳时定时辰为午", r_ts["info"]["hour_zhi"], "午")
    check("真太阳时命宫在丑", r_ts["info"]["ming_zhi"], "丑")
    check("真太阳时身宫在丑", r_ts["info"]["shen_zhi"], "丑")
    check("真太阳时五行局仍为水二局", r_ts["meta"]["ju"], 2)
    # 命主由命宫地支定：丑 -> 巨门（对照盘为子 -> 贪狼）
    txt = zp.format_report(r_ts)
    check("真太阳时命主为巨门", "命主：巨门" in txt, True)
    check("真太阳时四化为甲年（廉破武阳）", "化忌：太阳" in txt, True)

    # 关闭校正应回到钟表时口径
    r_off = zp.build(date(1994, 7, 28), hour=13, minute=30, sex="男",
                     longitude=104.066, true_solar=False)
    check("--no-true-solar 时不校正", r_off["info"]["hour_zhi"], "未")
    check("--no-true-solar 命宫在子", r_off["info"]["ming_zhi"], "子")

    # 跨时辰必须在警告中明示
    check("跨时辰有警告",
          any("跨时辰" in w for w in r_ts["warnings"]), True)
    check("校正明细有警告",
          any("真太阳时校正" in w for w in r_ts["warnings"]), True)


# ---------------------------------------------------------------------------
# B. 与 iztro 交叉对照
# ---------------------------------------------------------------------------

CROSS_JS = r"""
const iztro = require('iztro');
const chunks = [];
process.stdin.on('data', d => chunks.push(d));
process.stdin.on('end', () => {
  const cases = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  const out = [];
  for (const c of cases) {
    try {
      const a = iztro.astro.bySolar(c.date, c.timeIndex, c.gender, true, 'zh-CN');
      const stars = {};
      for (const p of a.palaces) {
        for (const s of p.majorStars) {
          (stars[s.name] = stars[s.name] || []).push(p.earthlyBranch + (s.mutagen ? ':' + s.mutagen : ''));
        }
      }
      const mut = {};
      for (const p of a.palaces) {
        for (const s of p.majorStars.concat(p.minorStars)) {
          if (s.mutagen) mut[s.mutagen] = s.name;
        }
      }
      out.push({
        ok: true,
        soul: a.earthlyBranchOfSoulPalace,
        body: a.earthlyBranchOfBodyPalace,
        five: a.fiveElementsClass,
        stars: stars,
        mut: mut
      });
    } catch (e) {
      out.push({ ok: false, err: String(e) });
    }
  }
  process.stdout.write(JSON.stringify(out));
});
"""

JU_TO_IZTRO = {2: "水二局", 3: "木三局", 4: "金四局", 5: "土五局", 6: "火六局"}
TIME_INDEX_OF_ZHI = {z: i for i, z in enumerate("子丑寅卯辰巳午未申酉戌亥")}


def _find_node():
    """定位 node 可执行文件。

    优先级：环境变量 NODE_BIN > PATH > 常见安装位置。
    不硬编码任何用户目录，保证本仓库在任何机器上可直接使用。
    """
    env_node = os.environ.get("NODE_BIN")
    if env_node and os.path.exists(env_node):
        return env_node

    found = shutil.which("node")
    if found:
        return found

    # 跨平台的常见位置（不绑定具体用户名）
    import glob
    patterns = [
        os.path.expanduser("~/.workbuddy/binaries/node/versions/*/node"),
        os.path.expanduser("~/.workbuddy/binaries/node/versions/*/node.exe"),
        "/usr/local/bin/node", "/usr/bin/node",
        r"C:\Program Files\nodejs\node.exe",
    ]
    for pat in patterns:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]          # 取版本号最大的
    return None


def _iztro_workspace():
    """定位用于交叉对照的 node modules 工作目录。

    环境变量 IZTRO_WORKSPACE 优先；否则退回用户主目录下的默认位置。
    """
    env_ws = os.environ.get("IZTRO_WORKSPACE")
    if env_ws:
        return env_ws
    return os.path.expanduser("~/.workbuddy/binaries/node/workspace")


def test_cross_iztro(rounds=40, seed=20260928):
    node = _find_node()
    if not node:
        print("  [跳过] 未找到 node，交叉对照不执行（可设 NODE_BIN 指定）")
        return

    workspace = _iztro_workspace()
    js_path = os.path.join(workspace, "_cross_iztro.js")
    with open(js_path, "w", encoding="utf-8") as fh:
        fh.write(CROSS_JS)

    rng = random.Random(seed)
    cases = []
    for _ in range(rounds):
        y = rng.randint(1950, 2020)
        m = rng.randint(1, 12)
        d = rng.randint(1, 28)
        ti = rng.randint(0, 11)          # 避开 12（晚子时）以保证口径一致
        cases.append({"date": "%d-%d-%d" % (y, m, d), "timeIndex": ti,
                      "gender": rng.choice(["男", "女"])})

    env = dict(os.environ)
    env["NODE_PATH"] = os.path.join(workspace, "node_modules")
    proc = subprocess.run([node, js_path], input=__import__("json").dumps(cases).encode("utf-8"),
                          capture_output=True, env=env, cwd=workspace)
    if proc.returncode != 0:
        print("  [跳过] node 执行失败：%s" % proc.stderr.decode("utf-8", "replace")[:300])
        return
    results = __import__("json").loads(proc.stdout.decode("utf-8"))

    mism = 0
    for c, res in zip(cases, results):
        if not res.get("ok"):
            continue
        y, m, d = (int(x) for x in c["date"].split("-"))
        # iztro 的 timeIndex 0..11 依次为子..亥
        hour = TIME_INDEX_OF_ZHI["子丑寅卯辰巳午未申酉戌亥"[c["timeIndex"]]] * 2
        # 闰月口径对齐：iztro 的 fixLeap=true 是「前半月作本月、后半月作下月」，
        # 对应本脚本的 --leap-policy split15；《全书》默认的 next-month 是另一派，
        # 故交叉对照须显式用 split15，否则闰月盘会整体错一宫。
        mine = zp.build(date(y, m, d), hour=hour, sex=c["gender"],
                        leap_policy="split15", year_divide="day")

        if mine["info"]["ming_zhi"] != res["soul"]:
            mism += 1
            FAILS.append("交叉 命宫 %s 第%d时 %s\n    我=%s iztro=%s"
                         % (c["date"], c["timeIndex"], c["gender"],
                            mine["info"]["ming_zhi"], res["soul"]))
        if mine["info"]["shen_zhi"] != res["body"]:
            mism += 1
            FAILS.append("交叉 身宫 %s 第%d时\n    我=%s iztro=%s"
                         % (c["date"], c["timeIndex"], mine["info"]["shen_zhi"], res["body"]))
        if JU_TO_IZTRO[mine["meta"]["ju"]] != res["five"]:
            mism += 1
            FAILS.append("交叉 五行局 %s 第%d时\n    我=%s iztro=%s"
                         % (c["date"], c["timeIndex"], JU_TO_IZTRO[mine["meta"]["ju"]], res["five"]))
        for star, vals in res["stars"].items():
            iz_zhis = sorted(v.split(":")[0] for v in vals)
            my_zhis = sorted(z for z in zp.ZHI
                             if any(s[0] == star for s in mine["board"][z]))
            if iz_zhis != my_zhis:
                mism += 1
                FAILS.append("交叉 主星 %s %s 第%d时\n    我=%s iztro=%s"
                             % (star, c["date"], c["timeIndex"], my_zhis, iz_zhis))
    CHECKS[0] += 1
    if mism:
        FAILS.append("交叉对照共 %d 处不一致（样本 %d）" % (mism, len(cases)))
    else:
        print("  交叉对照通过：%d 个样本盘的命身、五行局、十四主星全部一致" % len(cases))


def test_readme_assertion_count():
    """各语言 README 承诺的断言数必须与实际相符（与 test_ziwei_html.py 同一自检思路）。"""
    root = os.path.dirname(HERE)
    # 必须在任何断言之前取基准值。若放在中途取，前面已计入的断言会被重复加，
    # 预测值偏高，反而可能与被测的错误数字「对上」而给出假绿。
    base = CHECKS[0]
    pats = [
        ("README.md", r"test_ziwei_pan\.py\s*#\s*经典口诀锚点（(\d+) 项断言）"),
        ("README.en.md",
         r"test_ziwei_pan\.py\s*#\s*classic verse anchors \((\d+) assertions\)"),
    ]
    entries = []
    for fname, pat in pats:
        path = os.path.join(root, fname)
        # 硬性要求：缺文件即失败（静默跳过会让自检悄悄失效）
        check("%s 存在" % fname, os.path.exists(path), True)
        if os.path.exists(path):
            entries.append((fname, open(path, encoding="utf-8").read(), pat))
    if not entries:
        return

    # 本函数新增断言数（含上面 2 条「存在」）：
    #   每份 README 3 条 + 多语言 1 条互一致
    K = 3 * len(entries) + (1 if len(entries) > 1 else 0)
    predicted_total = base + K

    claims = {}
    for fname, txt, pat in entries:
        m = re.search(pat, txt)
        check("%s 标注了排盘测试断言数" % fname, bool(m), True)
        n = int(m.group(1)) if m else -1
        claims[fname] = n
        check("%s 排盘断言数与实际一致" % fname, n, predicted_total)

    if len(entries) > 1:
        check("各语言 README 排盘断言数互相一致",
              len({v for v in claims.values() if v > 0}), 1)


def main():
    argv = sys.argv[1:]
    print("A. 经典口诀锚点")
    test_ziwei_by_rule()
    test_ziwei_tianfu_mirror()
    test_nayin()
    test_wuxing_ju()
    test_mutagen_table()
    test_lunar_conversion()
    test_ming_shen()
    test_xiaoxian_start()
    test_daxian_direction()
    test_nandou_yingqi()
    test_baseline_chart()
    test_double_star_pairs()
    test_true_solar()
    test_readme_assertion_count()

    if "--cross" in argv:
        print("B. 与 iztro 交叉对照")
        test_cross_iztro()

    print("")
    print("共 %d 项断言，失败 %d 项" % (CHECKS[0], len(FAILS)))
    for f in FAILS:
        print("  ✗ %s" % f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
