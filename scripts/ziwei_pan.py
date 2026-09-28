#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""紫微斗数排盘（零第三方依赖，仅标准库）。

依明刊本《紫微斗数全书》三卷安星诀。时区一律按北京时间 UTC+8，
不用本机本地时区。农历与节气用定气定朔（与 bazi skill 的 pai_pan.py 同源），
确保「生日 -> 农历日」「年支 -> 生年太岁」两步不依赖查表。

算法锚点（供 QA 对照）
---------------------
本书与坊间主流排盘的差异集中在三处，脚本默认遵循《全书》，并提供开关：

1. **大限起宫**：本书卷三明言「阳男阴女从命前一宫起顺行（是父母宫），
   阴男阳女从命后一宫起逆行（是兄弟宫）」。坊间多数排盘软体则自命宫起。
   默认 `--daxian quanshu`（父母／兄弟宫起）；`--daxian common` 切到命宫起。

2. **闰月**：本书「凡有闰月具要依此为例」——闰月生者作下一月算。
   默认 `--leap-policy next-month`；坊间另有「闰月前十五日作上月、后十五日作下月」
   的分半法，用 `--leap-policy split15`。注意：此开关只影响**依生月**安的星
   与安身命；依**生日**起的紫微一律用真实农历日。

3. **晚子时（23:00-23:59）**：默认日柱与农历日均算次日（`--late-zishi next-day`），
   时支仍作子时。`--late-zishi same-day` 则保留当日。

其余锚点：

4. 命宫：寅起正月顺数至生月得月支宫，自该宫起子时**逆**数至生时；
   身宫：同起点**顺**数至生时。闰月按上月规则修正生月后再数。

5. 十二宫：男女俱自命宫**逆**布——命、兄弟、妻妾、子女、财帛、疾厄、
   迁移、奴仆、官禄、田宅、福德、父母。

6. 寅宫天干（五虎遁）：甲己丙寅、乙庚戊寅、丙辛庚寅、丁壬壬寅、戊癸甲寅。
   顺推至命宫得命宫干支，查六十甲子纳音得五行局：
   水二、木三、金四、土五、火六。局数即大限起始岁数。

7. 起紫微（局数除日数，商数宫前走；补数奇退偶进）：
       offset 从 0 起递增，直到 (农历日 + offset) % 局数 == 0；
       商 = (农历日 + offset) // 局数；
       自寅起 1 顺数至商所得之宫为本位，offset 为偶则顺进 offset 宫、
       为奇则逆退 offset 宫。
   校验锚点（据《全书》及通行口诀实例）：
       木三局廿七 -> 戌（offset 0，商 9）；火六局十三 -> 亥（offset 5，商 3）；
       土五局初六 -> 未（offset 4，商 2）；水二局初一 -> 丑；木三局初一 -> 辰；
       金四局初一 -> 亥；土五局初一 -> 午；火六局初二 -> 午、初四 -> 辰。
   天府：紫微与天府以寅申为轴镜像，`tianfu = 寅 起 1 顺数至 (12 - 紫微位)`。

8. 十四主星：紫微支逆布（紫微、天机、隔一太阳、武曲、天同、隔二廉贞）；
   天府支顺布（天府、太阴、贪狼、巨门、天相、天梁、隔三破军）。

9. 四化：唯一随生年干变化。见 MUTAGEN 表，与 chapters/ch10 同表。

10. 庙旺落陷：依 chapters/ch11 卷三「各主星庙陷速查」表。
    本书未载的零星组合按「平和」处理，并在报告中标 `*`。

11. 大限：起岁 = 局数，每宫十年，方向见第 1 条。
    小限：**不论阴阳，男顺女逆**；起宫由生年支三合定
    （寅午戌起辰、申子辰起戌、巳酉丑起未、亥卯未起丑），一年一宫。
    童限：一命二财三疾厄四妻五福六官禄，顺行，十五岁回命宫。

12. 长生十二神：水二局长生在申、木三局在亥、金四局在巳、土五局在申、
    火六局在寅；阳男阴女顺行，阴男阳女逆行。
    博士十二神：自禄存起，阳男阴女顺行，阴男阳女逆行。

13. 天伤天使：命前六位为天伤（恒在奴仆宫），命后六位为天使（恒在疾厄宫）。
"""

import argparse
import math
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

BJ = timezone(timedelta(hours=8))
J2000 = 2451545.0
UNIX_JD = 2440587.5

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
LUNAR_MONTH_NAMES = {
    1: "正月", 2: "二月", 3: "三月", 4: "四月", 5: "五月", 6: "六月",
    7: "七月", 8: "八月", 9: "九月", 10: "十月", 11: "十一月", 12: "十二月",
}
LUNAR_DAY_NAMES = {
    1: "初一", 2: "初二", 3: "初三", 4: "初四", 5: "初五", 6: "初六",
    7: "初七", 8: "初八", 9: "初九", 10: "初十", 11: "十一", 12: "十二",
    13: "十三", 14: "十四", 15: "十五", 16: "十六", 17: "十七", 18: "十八",
    19: "十九", 20: "二十", 21: "廿一", 22: "廿二", 23: "廿三", 24: "廿四",
    25: "廿五", 26: "廿六", 27: "廿七", 28: "廿八", 29: "廿九", 30: "三十",
}

# 十二宫次序（自命宫逆布）
PALACE_NAMES = (
    "命宫", "兄弟", "妻妾", "子女", "财帛", "疾厄",
    "迁移", "奴仆", "官禄", "田宅", "福德", "父母",
)
# 顺行次序用于大限（命前一宫=父母，即顺时针一宫）
PALACE_CW = ("命宫", "父母", "福德", "田宅", "官禄", "奴仆",
             "迁移", "疾厄", "财帛", "子女", "妻妾", "兄弟")

# 十二节（黄经、名、月支下标 寅=2）
JIE_DEFS = (
    (315, "立春", 2), (345, "惊蛰", 3), (15, "清明", 4), (45, "立夏", 5),
    (75, "芒种", 6), (105, "小暑", 7), (135, "立秋", 8), (165, "白露", 9),
    (195, "寒露", 10), (225, "立冬", 11), (255, "大雪", 0), (285, "小寒", 1),
)
ZHONGQI_LONGS = (0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330)

# 五虎遁：年干下标 -> 寅宫天干下标
YIN_GAN = {0: 2, 5: 2, 1: 4, 6: 4, 2: 6, 7: 6, 3: 8, 8: 8, 4: 0, 9: 0}

# 六十甲子纳音（每两柱一名，按 甲子..癸亥 顺序）
NAYIN_LABELS = (
    "海中金", "炉中火", "大林木", "路旁土", "剑锋金", "山头火",
    "涧下水", "城头土", "白蜡金", "杨柳木", "泉中水", "屋上土",
    "霹雳火", "松柏木", "长流水", "沙中金", "山下火", "平地木",
    "壁上土", "金箔金", "覆灯火", "天河水", "大驿土", "钗钏金",
    "桑柘木", "大溪水", "沙中土", "天上火", "石榴木", "大海水",
)
# 纳音五行 -> 局数
WUXING_TO_JU = {"水": 2, "木": 3, "金": 4, "土": 5, "火": 6}
JU_NAME = {2: "水二局", 3: "木三局", 4: "金四局", 5: "土五局", 6: "火六局"}

# 四化（生年干 -> 禄、权、科、忌）
MUTAGEN = {
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

# 天魁 / 天钺（生年干）
KUI_YUE = {
    "甲": ("丑", "未"), "戊": ("丑", "未"), "庚": ("丑", "未"),
    "乙": ("子", "申"), "己": ("子", "申"),
    "辛": ("午", "寅"),
    "壬": ("卯", "巳"), "癸": ("卯", "巳"),
    "丙": ("亥", "酉"), "丁": ("亥", "酉"),
}
# 禄存（生年干）
LUCUN = {"甲": "寅", "乙": "卯", "丙": "巳", "戊": "巳", "丁": "午", "己": "午",
         "庚": "申", "辛": "酉", "壬": "亥", "癸": "子"}
# 截路空亡（生年干）
JIELU = {"甲": ("申", "酉"), "己": ("申", "酉"), "乙": ("午", "未"), "庚": ("午", "未"),
         "丙": ("辰", "巳"), "辛": ("辰", "巳"), "丁": ("寅", "卯"), "壬": ("寅", "卯"),
         "戊": ("子", "丑"), "癸": ("子", "丑")}
# 旬中空亡（旬首 -> 所空二支）
XUNKONG = {"甲子": ("戌", "亥"), "甲戌": ("申", "酉"), "甲申": ("午", "未"),
           "甲午": ("辰", "巳"), "甲辰": ("寅", "卯"), "甲寅": ("子", "丑")}
# 天马（生年支三合）
TIANMA = {"寅": "申", "午": "申", "戌": "申", "申": "寅", "子": "寅", "辰": "寅",
          "巳": "亥", "酉": "亥", "丑": "亥", "亥": "巳", "卯": "巳", "未": "巳"}
# 火星 / 铃星 子时起点（生年支三合）
HUOLING = {"寅": ("丑", "卯"), "午": ("丑", "卯"), "戌": ("丑", "卯"),
           "申": ("寅", "戌"), "子": ("寅", "戌"), "辰": ("寅", "戌"),
           "巳": ("卯", "戌"), "酉": ("卯", "戌"), "丑": ("卯", "戌"),
           "亥": ("酉", "戌"), "卯": ("酉", "戌"), "未": ("酉", "戌")}
# 红鸾起点：卯上起子逆数至生年支；凤阁/龙池
# 长生起点（五行局）
CHANGSHENG_START = {2: "申", 3: "亥", 4: "巳", 5: "申", 6: "寅"}
CHANGSHENG_NAMES = ("长生", "沐浴", "冠带", "临官", "帝旺", "衰",
                    "病", "死", "墓", "绝", "胎", "养")
BOSHI_NAMES = ("博士", "力士", "青龙", "小耗", "将军", "奏书",
               "蜚廉", "喜神", "病符", "大耗", "伏兵", "官府")
BOSHI_DUTY = ("聪明", "权势", "喜气", "钱财", "威武", "福禄",
              "主孤", "喜气", "带疾", "退祖", "口舌", "官符")
# 小限起宫（生年支三合）
XIAOXIAN_START = {"寅": "辰", "午": "辰", "戌": "辰",
                  "申": "戌", "子": "戌", "辰": "戌",
                  "巳": "未", "酉": "未", "丑": "未",
                  "亥": "丑", "卯": "丑", "未": "丑"}
# 童限次序
TONGLIAN_ORDER = ("命宫", "财帛", "疾厄", "妻妾", "福德", "官禄")

# 庙旺落陷：星 -> {宫支: 等级}。等级用全书七级。
MIAO, WANG, DE, LI, PING, BUD, XIAN = "庙", "旺", "得地", "利益", "平和", "不得地", "落陷"
BRIGHTNESS = {
    "紫微": {"子": PING, "丑": MIAO, "寅": WANG, "卯": WANG, "辰": DE, "巳": WANG,
             "午": MIAO, "未": MIAO, "申": WANG, "酉": WANG, "戌": DE, "亥": WANG},
    "天府": {"子": MIAO, "丑": MIAO, "寅": MIAO, "卯": DE, "辰": MIAO, "巳": DE,
             "午": WANG, "未": MIAO, "申": DE, "酉": WANG, "戌": MIAO, "亥": DE},
    "天相": {"子": MIAO, "丑": MIAO, "寅": MIAO, "卯": XIAN, "辰": DE, "巳": DE,
             "午": MIAO, "未": DE, "申": MIAO, "酉": XIAN, "戌": DE, "亥": DE},
    "天梁": {"子": MIAO, "丑": WANG, "寅": MIAO, "卯": MIAO, "辰": MIAO, "巳": XIAN,
             "午": MIAO, "未": WANG, "申": XIAN, "酉": DE, "戌": MIAO, "亥": XIAN},
    "天同": {"子": WANG, "丑": BUD, "寅": LI, "卯": PING, "辰": PING, "巳": MIAO,
             "午": XIAN, "未": BUD, "申": WANG, "酉": PING, "戌": PING, "亥": MIAO},
    "天机": {"子": MIAO, "丑": XIAN, "寅": DE, "卯": WANG, "辰": WANG, "巳": PING,
             "午": MIAO, "未": XIAN, "申": DE, "酉": WANG, "戌": LI, "亥": PING},
    "太阳": {"子": XIAN, "丑": BUD, "寅": WANG, "卯": MIAO, "辰": WANG, "巳": WANG,
             "午": WANG, "未": DE, "申": DE, "酉": PING, "戌": XIAN, "亥": XIAN},
    "太阴": {"子": MIAO, "丑": MIAO, "寅": WANG, "卯": XIAN, "辰": XIAN, "巳": XIAN,
             "午": BUD, "未": BUD, "申": LI, "酉": WANG, "戌": WANG, "亥": MIAO},
    "武曲": {"子": WANG, "丑": MIAO, "寅": DE, "卯": LI, "辰": MIAO, "巳": PING,
             "午": WANG, "未": MIAO, "申": DE, "酉": LI, "戌": MIAO, "亥": PING},
    "贪狼": {"子": WANG, "丑": MIAO, "寅": PING, "卯": LI, "辰": MIAO, "巳": XIAN,
             "午": WANG, "未": MIAO, "申": PING, "酉": LI, "戌": MIAO, "亥": XIAN},
    "廉贞": {"子": PING, "丑": LI, "寅": MIAO, "卯": PING, "辰": LI, "巳": XIAN,
             "午": PING, "未": LI, "申": MIAO, "酉": PING, "戌": LI, "亥": XIAN},
    "巨门": {"子": WANG, "丑": BUD, "寅": MIAO, "卯": MIAO, "辰": XIAN, "巳": WANG,
             "午": WANG, "未": BUD, "申": MIAO, "酉": MIAO, "戌": XIAN, "亥": WANG},
    "七杀": {"子": WANG, "丑": MIAO, "寅": MIAO, "卯": WANG, "辰": MIAO, "巳": PING,
             "午": WANG, "未": MIAO, "申": MIAO, "酉": WANG, "戌": MIAO, "亥": PING},
    "破军": {"子": MIAO, "丑": WANG, "寅": DE, "卯": XIAN, "辰": WANG, "巳": PING,
             "午": MIAO, "未": WANG, "申": DE, "酉": XIAN, "戌": WANG, "亥": PING},
    "文昌": {"子": DE, "丑": MIAO, "寅": XIAN, "卯": LI, "辰": DE, "巳": MIAO,
             "午": XIAN, "未": LI, "申": DE, "酉": MIAO, "戌": XIAN, "亥": LI},
    "文曲": {"子": DE, "丑": MIAO, "寅": XIAN, "卯": LI, "辰": DE, "巳": MIAO,
             "午": XIAN, "未": LI, "申": DE, "酉": MIAO, "戌": XIAN, "亥": LI},
    "擎羊": {"子": XIAN, "丑": MIAO, "寅": PING, "卯": XIAN, "辰": MIAO, "巳": PING,
             "午": XIAN, "未": MIAO, "申": PING, "酉": XIAN, "戌": MIAO, "亥": PING},
    "陀罗": {"子": PING, "丑": MIAO, "寅": XIAN, "卯": PING, "辰": MIAO, "巳": XIAN,
             "午": PING, "未": MIAO, "申": XIAN, "酉": PING, "戌": MIAO, "亥": XIAN},
    "火星": {"子": XIAN, "丑": DE, "寅": MIAO, "卯": LI, "辰": XIAN, "巳": DE,
             "午": MIAO, "未": LI, "申": XIAN, "酉": DE, "戌": MIAO, "亥": LI},
    "铃星": {"子": XIAN, "丑": DE, "寅": MIAO, "卯": LI, "辰": XIAN, "巳": DE,
             "午": MIAO, "未": LI, "申": XIAN, "酉": DE, "戌": MIAO, "亥": LI},
    "禄存": {z: MIAO for z in ZHI},
}
# 十四主星（用于报告排序与星性表）
MAJOR_STARS = ("紫微", "天机", "太阳", "武曲", "天同", "廉贞",
               "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军")
# 命主（命宫地支）
SOUL_STAR = {"子": "贪狼", "丑": "巨门", "亥": "巨门", "寅": "禄存", "戌": "禄存",
             "卯": "文曲", "酉": "文曲", "辰": "廉贞", "申": "廉贞",
             "巳": "武曲", "未": "武曲", "午": "破军"}
# 身主（生年支）
BODY_STAR = {"子": "火星", "午": "火星", "丑": "天相", "未": "天相",
             "寅": "天梁", "申": "天梁", "卯": "天同", "酉": "天同",
             "辰": "文昌", "戌": "文昌", "巳": "天机", "亥": "天机"}
# 十二支所忌（ch15 卷三）
ZHI_TABOO = {
    "子": "忌寅申岁限，及忌子午岁限相冲",
    "丑": "忌午丑岁限，及忌七杀星", "午": "忌午丑岁限，及忌七杀星",
    "寅": "忌巳亥岁限，及忌卯酉寅申相冲", "卯": "忌巳亥岁限，及忌卯酉寅申相冲",
    "辰": "忌逢巳年及行到巳限；行到辰为天罗，行到戌为地网",
    "巳": "忌逢巳年及行到巳限；行到辰为天罗，行到戌为地网",
    "申": "忌逢火铃二星，及忌寅年冲",
    "未": "忌逢酉戌岁限，又忌见擎羊在四墓宫",
    "戌": "忌遇羊陀灾重；行到戌为地网，到辰为天罗",
    "亥": "忌遇羊陀灾重；行到戌为地网，到辰为天罗",
    "酉": "忌羊陀岁限及忌行卯宫限，及卯年相冲",
}
# 纳音五行忌宫（ch15 立命行限宫歌）
NAYIN_TABOO = {"金": ("坎", "子"), "木": ("离", "午"), "水": ("艮", "丑寅"),
               "火": ("兑", "酉"), "土": ("震巽东南", "卯辰巳")}
# 解灾四星 / 三合解七杀重逢
SOLVE_JIAXIAN = ("紫微", "天同", "天梁", "贪狼")
SOLVE_QISHA = ("紫微", "天相", "禄存")

SHICHEN_MID = {"子": (0, 0), "丑": (2, 0), "寅": (4, 0), "卯": (6, 0),
               "辰": (8, 0), "巳": (10, 0), "午": (12, 0), "未": (14, 0),
               "申": (16, 0), "酉": (18, 0), "戌": (20, 0), "亥": (22, 0)}


# ---------------------------------------------------------------------------
# 时间 / 儒略日（北京 UTC+8）
# ---------------------------------------------------------------------------

def delta_t_seconds(year):
    """TT−UTC 近似秒（Espenak/Meeus 分段多项式），1900–2100 到分钟级。"""
    y = float(year)
    t = y - 2000.0
    if y < 1920:
        t1 = y - 1900.0
        return -2.79 + 1.494119 * t1 - 0.0598939 * t1 ** 2 + 0.0061966 * t1 ** 3 - 0.000197 * t1 ** 4
    if y < 1941:
        t1 = y - 1920.0
        return 21.20 + 0.84493 * t1 - 0.076100 * t1 ** 2 + 0.0020936 * t1 ** 3
    if y < 1961:
        t1 = y - 1950.0
        return 29.07 + 0.407 * t1 - t1 ** 2 / 233.0 + t1 ** 3 / 2547.0
    if y < 1986:
        t1 = y - 1975.0
        return 45.45 + 1.067 * t1 - t1 ** 2 / 260.0 - t1 ** 3 / 718.0
    if y < 2005:
        t1 = y - 2000.0
        return (63.86 + 0.3345 * t1 - 0.060374 * t1 ** 2 + 0.0017275 * t1 ** 3
                + 0.000651814 * t1 ** 4 + 0.00002373599 * t1 ** 5)
    if y < 2050:
        return 62.92 + 0.32217 * t + 0.005589 * t * t
    return -20.0 + 32.0 * ((y - 1820.0) / 100.0) ** 2 - 0.5628 * (2150.0 - y)


def jd_from_datetime_utc(dt):
    utc = dt.astimezone(timezone.utc)
    unix = (utc - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()
    return UNIX_JD + unix / 86400.0


def datetime_utc_from_jd(jd):
    seconds = (jd - UNIX_JD) * 86400.0
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def jd_tt_to_beijing(jd_tt):
    year = 2000.0 + (jd_tt - J2000) / 365.242189
    utc_jd = jd_tt - delta_t_seconds(year) / 86400.0
    return datetime_utc_from_jd(utc_jd).astimezone(BJ)


def beijing(year, month, day, hour=0, minute=0, second=0):
    return datetime(year, month, day, hour, minute, second, tzinfo=BJ)


def jdn(year, month, day):
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


# ---------------------------------------------------------------------------
# 太阳视黄经 / 二十四节气
# ---------------------------------------------------------------------------

def sun_apparent_longitude(jd_tt):
    T = (jd_tt - J2000) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T
    mr = math.radians(M)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(mr)
         + (0.019993 - 0.000101 * T) * math.sin(2.0 * mr)
         + 0.000289 * math.sin(3.0 * mr))
    omega = 125.04 - 1934.136 * T
    lam = L0 + C - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    return lam % 360.0


def _lon_delta(actual, target):
    return (actual - target + 180.0) % 360.0 - 180.0


@lru_cache(maxsize=4096)
def solar_term_jd(year, longitude):
    """该公历年、目标黄经的定气 TT 儒略日。立春 = 315°。"""
    year = int(year)
    longitude = float(longitude) % 360.0
    delta_lon = (longitude - 280.46646) % 360.0
    jd0 = J2000 + (year - 2000) * 365.242189 + delta_lon / 0.98564736
    lo, hi = jd0 - 8.0, jd0 + 8.0
    for _ in range(52):
        mid = (lo + hi) / 2.0
        if _lon_delta(sun_apparent_longitude(mid), longitude) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def solar_term_beijing(year, longitude):
    return jd_tt_to_beijing(solar_term_jd(year, longitude))


# ---------------------------------------------------------------------------
# 真太阳时（均时差 + 经度时差）
# ---------------------------------------------------------------------------

def equation_of_time_minutes(year, month, day, hour=12):
    """均时差 EoT（分）。NOAA 简化式，精度约 ±0.5 分，足够判定时辰边界。"""
    cum = [0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = cum[month] + day
    gamma = 2.0 * math.pi / 365.0 * (doy - 1 + (hour - 12) / 24.0)
    return 229.18 * (0.000075 + 0.001868 * math.cos(gamma)
                     - 0.032077 * math.sin(gamma)
                     - 0.014615 * math.cos(2 * gamma)
                     - 0.040849 * math.sin(2 * gamma))


def true_solar_shift_minutes(longitude, year, month, day, hour=12):
    """总校正量（分）= 经度时差 + 均时差。东经小于 120 度为负。"""
    return (float(longitude) - 120.0) * 4.0 + equation_of_time_minutes(year, month, day, hour)


# ---------------------------------------------------------------------------
# 定朔（Meeus 第 49 章）
# ---------------------------------------------------------------------------

def new_moon_jde(k):
    T = k / 1236.85
    jde = (2451550.09766 + 29.530588861 * k + 0.00015437 * T * T
           - 0.000000150 * T ** 3 + 0.00000000073 * T ** 4)
    E = 1.0 - 0.002516 * T - 0.0000074 * T * T
    M = math.radians(2.5534 + 29.10535670 * k - 0.0000014 * T * T - 0.00000011 * T ** 3)
    Mp = math.radians(201.5643 + 385.81693528 * k + 0.0107582 * T * T
                      + 0.00001238 * T ** 3 - 0.000000058 * T ** 4)
    F = math.radians(160.7108 + 390.67050284 * k - 0.0016118 * T * T
                     - 0.00000227 * T ** 3 + 0.000000011 * T ** 4)
    omega = math.radians(124.7746 - 1.56375588 * k + 0.0020672 * T * T + 0.00000215 * T ** 3)
    args = (Mp, M, 2 * Mp, 2 * F, Mp - M, Mp + M, 2 * M, Mp - 2 * F, Mp + 2 * F,
            2 * Mp + M, 3 * Mp, M + 2 * F, M - 2 * F, 2 * Mp - M, omega,
            Mp + 2 * M, 2 * Mp - 2 * F, 3 * M, Mp + M - 2 * F, 2 * Mp + 2 * F,
            Mp + M + 2 * F, Mp - M + 2 * F, Mp - M - 2 * F, 3 * Mp + M, 4 * Mp)
    coef = (-0.40720, 0.17241 * E, 0.01608, 0.01039, 0.00739 * E, -0.00514 * E,
            0.00208 * E * E, -0.00111, -0.00057, 0.00056 * E, -0.00042, 0.00042 * E,
            0.00038 * E, -0.00024 * E, -0.00017, -0.00007, 0.00004, 0.00004,
            0.00003, 0.00003, -0.00003, 0.00003, -0.00002, -0.00002, 0.00002)
    jde += sum(c * math.sin(a) for c, a in zip(coef, args))
    A = (299.77 + 0.107408 * k - 0.009173 * T * T, 251.88 + 0.016321 * k,
         251.83 + 26.651886 * k, 349.42 + 36.412478 * k, 84.66 + 18.206239 * k,
         141.74 + 53.303771 * k, 207.14 + 2.453732 * k, 154.84 + 7.306860 * k,
         34.52 + 27.261239 * k, 207.19 + 0.121824 * k, 291.34 + 1.844379 * k,
         161.72 + 24.198154 * k, 239.56 + 25.513099 * k, 331.55 + 3.592518 * k)
    Ac = (325, 165, 164, 126, 110, 62, 60, 56, 47, 42, 40, 37, 35, 23)
    jde += sum(c * 1e-6 * math.sin(math.radians(a)) for c, a in zip(Ac, A))
    return jde


def _k_near(jd):
    return int(round((jd - 2451550.09766) / 29.530588861))


def last_new_moon_k_on_or_before(jd_tt):
    k = _k_near(jd_tt)
    while new_moon_jde(k) > jd_tt:
        k -= 1
    while new_moon_jde(k + 1) <= jd_tt:
        k += 1
    return k


# ---------------------------------------------------------------------------
# 农历（冬至十一月 + 无中气置闰）
# ---------------------------------------------------------------------------

def _zhongqi_jds(year):
    out = []
    for y in (year - 1, year, year + 1):
        for lon in ZHONGQI_LONGS:
            out.append(solar_term_jd(y, lon))
    return out


@lru_cache(maxsize=256)
def lunar_months_between_dongzhi(dongzhi_year):
    """自「dongzhi_year 冬至所在十一月」起到下一年冬至月之前的各农历月。

    返回 tuple of dict: year, month, leap, start(date), days, shuo_dt

    **历法要点**：农历置闰以「日」为粒度——朔与中气都取北京日期，
    某月的首日至次月首日之间（前闭后开）若不含任何中气日，该月即闰月。
    若改用精确时刻比较，则朔与中气同日而时刻先后不同时，闰月会错位
    （例如 1987 年闰六月、1984 年闰十月、1993 年闰三月）。
    """
    y = int(dongzhi_year)
    dz0 = jd_tt_to_beijing(solar_term_jd(y, 270)).date()
    dz1 = jd_tt_to_beijing(solar_term_jd(y + 1, 270)).date()

    k = _k_near(solar_term_jd(y, 270))
    while jd_tt_to_beijing(new_moon_jde(k)).date() > dz0:
        k -= 1
    while jd_tt_to_beijing(new_moon_jde(k + 1)).date() <= dz0:
        k += 1
    k0 = k
    k = k0
    while jd_tt_to_beijing(new_moon_jde(k + 1)).date() <= dz1:
        k += 1
    k1 = k

    moons = [new_moon_jde(kk) for kk in range(k0, k1 + 1)]
    dates = [jd_tt_to_beijing(m).date() for m in moons]
    n = len(moons) - 1
    zhong_dates = [jd_tt_to_beijing(z).date() for z in _zhongqi_jds(y)]

    leap_index = None
    if n == 13:
        for i in range(n):
            if not any(dates[i] <= zd < dates[i + 1] for zd in zhong_dates):
                leap_index = i
                break

    months = []
    month_num = 11
    lunar_year = y
    for i in range(n):
        is_leap = leap_index is not None and i == leap_index
        if i > 0 and not is_leap:
            month_num += 1
            if month_num == 13:
                month_num = 1
                lunar_year += 1
        months.append({"year": lunar_year, "month": month_num, "leap": is_leap,
                       "start": dates[i], "days": (dates[i + 1] - dates[i]).days,
                       "shuo_dt": jd_tt_to_beijing(moons[i])})
    return tuple(months)


def lunar_months_covering_solar_year(solar_year):
    a = lunar_months_between_dongzhi(solar_year - 1)
    b = lunar_months_between_dongzhi(solar_year)
    seen, out = set(), []
    for m in a + b:
        key = (m["start"], m["year"], m["month"], m["leap"])
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    out.sort(key=lambda x: x["start"])
    return out


def solar_to_lunar(y, m, d):
    """公历日 -> (农历年, 月, 日, 是否闰月)。

    精度说明：朔用 Meeus 定朔简式（精度约 1–2 分钟）。若某朔恰好落在子夜
    前后数分钟内，换算结果可能与官方历书差一日（1900–1920 年间偶见，约
    0.3%）。此类日期请以紫金山天文台历书或权威农历工具复核。
    """
    target = date(y, m, d)
    months = lunar_months_covering_solar_year(y)
    if y - 1 >= 1890:
        months = list(lunar_months_between_dongzhi(y - 2)) + list(months)
    for info in months:
        start = info["start"]
        end = start + timedelta(days=info["days"])
        if start <= target < end:
            return info["year"], info["month"], (target - start).days + 1, info["leap"]
    raise ValueError("无法把 %04d-%02d-%02d 换成农历（超出推算范围）" % (y, m, d))


def shuo_near_midnight(xy, m, d, tol_minutes=6):
    """该日附近是否有朔落在子夜 ±tol 分钟内（用于提示换算可能差一日）。"""
    target = date(xy, m, d)
    k = _k_near(jdn(xy, m, d) + 0.5)
    for kk in (k - 1, k, k + 1):
        dt = jd_tt_to_beijing(new_moon_jde(kk))
        if dt.date() == target:
            minutes = dt.hour * 60 + dt.minute
            if minutes <= tol_minutes or minutes >= 24 * 60 - tol_minutes:
                return True
    return False


def lunar_to_solar(ly, lm, ld, leap=False):
    months = (list(lunar_months_between_dongzhi(ly - 1))
              + list(lunar_months_between_dongzhi(ly)))
    found = None
    for info in months:
        if info["year"] == ly and info["month"] == lm and bool(info["leap"]) == bool(leap):
            found = info
            break
    if found is None:
        name = LUNAR_MONTH_NAMES.get(lm, str(lm) + "月")
        raise ValueError("农历 %d年%s%s不存在" % (ly, "闰" if leap else "", name))
    if ld < 1 or ld > found["days"]:
        raise ValueError("农历 %d年%s%s只有 %d 天"
                         % (ly, "闰" if leap else "", LUNAR_MONTH_NAMES.get(lm, str(lm) + "月"),
                            found["days"]))
    return found["start"] + timedelta(days=ld - 1)


def format_lunar(ly, lm, ld, leap):
    return "%d年%s%s%s" % (ly, "闰" if leap else "",
                           LUNAR_MONTH_NAMES.get(lm, str(lm) + "月"),
                           LUNAR_DAY_NAMES.get(ld, str(ld)))


def lunar_month_days(ly, lm, leap=False):
    months = (list(lunar_months_between_dongzhi(ly - 1))
              + list(lunar_months_between_dongzhi(ly)))
    for info in months:
        if info["year"] == ly and info["month"] == lm and bool(info["leap"]) == bool(leap):
            return info["days"]
    return 30


# ---------------------------------------------------------------------------
# 干支 / 纳音 / 五行局
# ---------------------------------------------------------------------------

def gz_from_index(idx):
    idx = int(idx) % 60
    return GAN[idx % 10], ZHI[idx % 12]


def year_gz_index(year):
    """立春后的年干支序号，1984 = 甲子 = 0。"""
    return (int(year) - 4) % 60


def day_gz_index(year, month, day):
    """日柱序号。锚点 1990-05-15 = 庚辰（序号 16）。"""
    return (jdn(year, month, day) + 49) % 60


def year_gz_of(birth_dt, year_divide="exact"):
    """定年干支。

    year_divide="exact" —— 以立春**精确时刻**分界（本脚本默认，与八字同口径）。
    year_divide="day"   —— 立春**当日**即算新年（部分斗数排盘软体如 iztro 采用，
                            便于与外部工具对照）。
    """
    year = birth_dt.year
    lichun = solar_term_beijing(year, 315)
    if year_divide == "exact":
        if birth_dt < lichun:
            year -= 1
    else:
        if birth_dt.date() < lichun.date():
            year -= 1
    g, z = gz_from_index(year_gz_index(year))
    return year, g, z


def nayin_of(gan, zhi):
    """干支 -> (纳音名, 纳音五行)。"""
    gi, zi = GAN.index(gan), ZHI.index(zhi)
    for n in range(60):
        if n % 10 == gi and n % 12 == zi:
            idx = n
            break
    else:
        raise ValueError("非法干支 %s%s" % (gan, zhi))
    return NAYIN_LABELS[idx // 2], NAYIN_LABELS[idx // 2][-1]


# ---------------------------------------------------------------------------
# 盘面结构
# ---------------------------------------------------------------------------

def zhi_index(zhi):
    return ZHI.index(zhi)


def shift(zhi, steps):
    """地支位移，steps 正为顺行。"""
    return ZHI[(ZHI.index(zhi) + steps) % 12]


# 以「寅」为 0 的盘面索引，便于与 iztro 等主流实现对照
def zhi_to_pan(zhi):
    return (ZHI.index(zhi) - 2) % 12


def pan_to_zhi(idx):
    return ZHI[(idx + 2) % 12]


def palace_names_by_branch(ming_zhi):
    """返回 {地支: 宫名}，自命宫逆布。"""
    mapping = {}
    for i, name in enumerate(PALACE_NAMES):
        mapping[shift(ming_zhi, -i)] = name
    return mapping


def stars_by_branch(ming_zhi, shen_zhi, year_gan, year_zhi, month_num, day_num,
                    hour_zhi, is_yang, is_male):
    """按《全书》安星诀铺满全盘。

    返回 {地支: [(星名, 庙陷 or None, 四化 or None), ...]}
    """
    board = {z: [] for z in ZHI}

    def put(zhi, star, brightness=None, mutagen=None):
        board[zhi].append((star, brightness, mutagen))

    # --- 五行局（先算，供长生十二神用）---
    yin_gan = GAN[YIN_GAN[GAN.index(year_gan)]]  # 寅宫天干
    ming_gan = GAN[(GAN.index(yin_gan) + zhi_to_pan(ming_zhi)) % 10]
    _, ju_wx = nayin_of(ming_gan, ming_zhi)
    ju = WUXING_TO_JU[ju_wx]

    # --- 起紫微 / 天府 ---
    # 「局数除日数，商数宫前走」：补最小 offset 使 (日+offset) 整除局数，
    # 商数自寅起 1 顺数所得之宫即本位；再按补数**奇退偶进**（奇则逆回 offset 宫）。
    offset = 0
    while (day_num + offset) % ju != 0:
        offset += 1
    quotient = (day_num + offset) // ju
    base_pos = (quotient - 1) % 12
    ziwei_pos = (base_pos + offset) % 12 if offset % 2 == 0 else (base_pos - offset) % 12
    ziwei_zhi = pan_to_zhi(ziwei_pos)
    tianfu_pos = (12 - ziwei_pos) % 12
    tianfu_zhi = pan_to_zhi(tianfu_pos)

    # --- 北斗支（逆布）：紫微、天机、隔一太阳、武曲、天同、隔二廉贞 ---
    beidou = (("紫微", 0), ("天机", -1), ("太阳", -3), ("武曲", -4),
              ("天同", -5), ("廉贞", -8))
    for star, step in beidou:
        put(shift(ziwei_zhi, step), star, BRIGHTNESS[star][shift(ziwei_zhi, step)])
    # --- 南斗支（顺布）：天府、太阴、贪狼、巨门、天相、天梁、隔三破军 ---
    nandou = (("天府", 0), ("太阴", 1), ("贪狼", 2), ("巨门", 3),
              ("天相", 4), ("天梁", 5), ("七杀", 6), ("破军", 10))
    for star, step in nandou:
        put(shift(tianfu_zhi, step), star, BRIGHTNESS[star][shift(tianfu_zhi, step)])

    # --- 依生时 ---
    # 文昌：戌起子时逆；文曲：辰起子时顺
    steps = ZHI.index(hour_zhi)  # 子=0
    wen = shift("戌", -steps)
    qu = shift("辰", steps)
    put(wen, "文昌", BRIGHTNESS["文昌"][wen])
    put(qu, "文曲", BRIGHTNESS["文曲"][qu])
    # 地劫：亥起子时顺；地空：亥起子时逆
    jie = shift("亥", steps)
    kong = shift("亥", -steps)
    put(jie, "地劫")
    put(kong, "地空")
    # 台辅：午起子时顺；封诰：寅起子时顺
    put(shift("午", steps), "台辅")
    put(shift("寅", steps), "封诰")

    # --- 依生月（month_num 为修正后的生月，1..12）---
    msteps = month_num - 1
    zuo = shift("辰", msteps)
    you = shift("戌", -msteps)
    put(zuo, "左辅")
    put(you, "右弼")
    put(shift("酉", msteps), "天刑")
    put(shift("丑", msteps), "天姚")

    # --- 依生年干 ---
    kui, yue = KUI_YUE[year_gan]
    put(kui, "天魁")
    put(yue, "天钺")
    lu = LUCUN[year_gan]
    put(lu, "禄存", BRIGHTNESS["禄存"][lu])
    yang = shift(lu, 1)
    tuo = shift(lu, -1)
    put(yang, "擎羊", BRIGHTNESS["擎羊"][yang])
    put(tuo, "陀罗", BRIGHTNESS["陀罗"][tuo])
    for z in JIELU[year_gan]:
        put(z, "截空")

    # --- 依生年支 ---
    put(TIANMA[year_zhi], "天马")
    huo_start, ling_start = HUOLING[year_zhi]
    huo = shift(huo_start, steps)
    ling = shift(ling_start, steps)
    put(huo, "火星", BRIGHTNESS["火星"][huo])
    put(ling, "铃星", BRIGHTNESS["铃星"][ling])
    # 天哭：午起子逆数至生年支；天虚：午起子顺数至生年支
    ysteps = ZHI.index(year_zhi)
    put(shift("午", -ysteps), "天哭")
    put(shift("午", ysteps), "天虚")
    # 龙池：辰起子顺至年支；凤阁：戌起子逆至年支
    put(shift("辰", ysteps), "龙池")
    put(shift("戌", -ysteps), "凤阁")
    # 红鸾：卯起子逆至年支；天喜为对宫
    hong = shift("卯", -ysteps)
    put(hong, "红鸾")
    put(shift(hong, 6), "天喜")
    # 孤辰寡宿
    gu_gua = {"寅": ("巳", "丑"), "卯": ("巳", "丑"), "辰": ("巳", "丑"),
              "巳": ("申", "辰"), "午": ("申", "辰"), "未": ("申", "辰"),
              "申": ("亥", "未"), "酉": ("亥", "未"), "戌": ("亥", "未"),
              "亥": ("寅", "戌"), "子": ("寅", "戌"), "丑": ("寅", "戌")}
    put(gu_gua[year_zhi][0], "孤辰")
    put(gu_gua[year_zhi][1], "寡宿")
    # 华盖 / 咸池
    hua_gai = {"子": "辰", "辰": "辰", "申": "辰", "丑": "丑", "巳": "丑", "酉": "丑",
               "寅": "戌", "午": "戌", "戌": "戌", "卯": "未", "未": "未", "亥": "未"}
    xian_chi = {"子": "酉", "辰": "酉", "申": "酉", "丑": "午", "巳": "午", "酉": "午",
                "寅": "卯", "午": "卯", "戌": "卯", "卯": "子", "未": "子", "亥": "子"}
    put(hua_gai[year_zhi], "华盖")
    put(xian_chi[year_zhi], "咸池")
    # 破碎 / 蜚廉
    po_sui = {"子": "巳", "午": "巳", "卯": "巳", "酉": "巳",
              "寅": "酉", "申": "酉", "巳": "酉", "亥": "酉",
              "辰": "丑", "戌": "丑", "丑": "丑", "未": "丑"}
    put(po_sui[year_zhi], "破碎")

    # --- 依生日：三台（左辅起初一顺数）、八座（右弼起初一逆数）、恩光天贵 ---
    put(shift(zuo, day_num - 1), "三台")
    put(shift(you, -(day_num - 1)), "八座")
    put(shift(wen, day_num - 2), "恩光")
    put(shift(qu, day_num - 2), "天贵")

    # --- 依命宫：天伤在奴仆宫（命逆七）、天使在疾厄宫（命逆五）---
    put(shift(ming_zhi, -7), "天伤")
    put(shift(ming_zhi, -5), "天使")

    # --- 天才（命宫起子顺至年支）、天寿（身宫起子顺至年支）---
    put(shift(ming_zhi, ysteps), "天才")
    put(shift(shen_zhi, ysteps), "天寿")

    # --- 长生十二神 ---
    cs_start = CHANGSHENG_START[ju]
    forward = (is_yang and is_male) or ((not is_yang) and (not is_male))
    for i, name in enumerate(CHANGSHENG_NAMES):
        z = shift(cs_start, i if forward else -i)
        put(z, name)

    # --- 博士十二神 ---
    for i, name in enumerate(BOSHI_NAMES):
        z = shift(lu, i if forward else -i)
        put(z, name, None, None)

    # --- 四化 ---
    lu_x, quan_x, ke_x, ji_x = MUTAGEN[year_gan]
    mutagen_map = {lu_x: "禄", quan_x: "权", ke_x: "科", ji_x: "忌"}
    for z in ZHI:
        seen_names = set()
        new = []
        for star, b, m in board[z]:
            if star in seen_names:
                continue          # 同名星（如两种来源的蜚廉/破碎）只留一处
            seen_names.add(star)
            new.append((star, b, mutagen_map.get(star, m)))
        board[z] = new

    meta = {
        "ming_gan": ming_gan, "ju": ju, "ju_wx": ju_wx,
        "ziwei_zhi": ziwei_zhi, "tianfu_zhi": tianfu_zhi,
        "mutagen": (lu_x, quan_x, ke_x, ji_x),
    }
    return board, meta


# 供旬中空亡使用（模块级，避免重复算）
day_gz_index_num = 0


def apply_xunkong(board, year_gan, year_zhi):
    """按年柱旬首补旬中空亡（ch10：甲子旬空戌亥，甲寅旬空子丑…）。"""
    gi, zi = GAN.index(year_gan), ZHI.index(year_zhi)
    head = 0
    for n in range(60):
        if n % 10 == gi and n % 12 == zi:
            head = (n // 10) * 10
            break
    key = "".join(gz_from_index(head))
    for z in XUNKONG[key]:
        board[z].append(("旬空", None, None))


def build_palaces(ming_zhi, board, meta, year_gan, year_zhi, is_yang, is_male):
    names = palace_names_by_branch(ming_zhi)
    yin_gan = GAN[YIN_GAN[GAN.index(year_gan)]]
    ju = meta["ju"]
    palaces = []
    # 自寅起顺时针列出十二宫（便于输出成方盘）
    for i in range(12):
        z = pan_to_zhi(i)
        gan = GAN[(GAN.index(yin_gan) + i) % 10]
        stars = [s for s in board[z]]
        palaces.append({
            "zhi": z,
            "gan": gan,
            "name": names[z],
            "stars": stars,
        })
    return palaces


def compute(start_year, month_num, day_num, hour_zhi, is_male, year_gan, year_zhi,
            board, meta, hour_known=True):
    """大限 / 小限 / 童限 / 流年。"""
    ming_zhi = meta["ming_zhi"]
    ju = meta["ju"]
    is_yang = GAN.index(year_gan) % 2 == 0
    forward = (is_yang and is_male) or ((not is_yang) and (not is_male))

    # --- 大限：全书自命前一宫（父母）顺行 / 命后一宫（兄弟）逆行 ---
    names = palace_names_by_branch(ming_zhi)
    daxian = []
    start_from = shift(ming_zhi, 1) if forward else shift(ming_zhi, -1)
    for i in range(12):
        z = shift(start_from, i if forward else -i)
        lo = ju + 10 * i
        daxian.append({"zhi": z, "palace": names[z], "range": (lo, lo + 9)})

    # 对照用：自命宫起（坊间主流）
    daxian_common = []
    for i in range(12):
        z = shift(ming_zhi, i if forward else -i)
        lo = ju + 10 * i
        daxian_common.append({"zhi": z, "palace": names[z], "range": (lo, lo + 9)})

    # --- 小限：不论阴阳，男顺女逆 ---
    xiao_start = XIAOXIAN_START[year_zhi]
    xiaoxian = []
    for i in range(12):
        z = shift(xiao_start, i if is_male else -i)
        xiaoxian.append({"zhi": z, "palace": names[z], "ages": [(12 * j + i + 1) for j in range(9)]})

    # --- 童限 ---
    tonglian = []
    for i, pname in enumerate(TONGLIAN_ORDER):
        tonglian.append({"age": i + 1, "palace": pname})
    tonglian.append({"age": 15, "palace": "命宫"})

    return {
        "forward": forward,
        "daxian": daxian,
        "daxian_common": daxian_common,
        "xiaoxian": xiaoxian,
        "tonglian": tonglian,
    }


def age_at(daxian_list, age):
    for row in daxian_list:
        lo, hi = row["range"]
        if lo <= age <= hi:
            return row
    return None


def xiaoxian_at(xiaoxian_list, age):
    for row in xiaoxian_list:
        if age in row["ages"]:
            return row
    return None


def liunian_gz(year):
    g, z = gz_from_index(year_gz_index(year))
    return g + z


# ---------------------------------------------------------------------------
# 组装与报告
# ---------------------------------------------------------------------------

def resolve(birth_solar, hour, minute, sex, leap_policy, late_zishi, year_divide="exact"):
    """由公历日期与钟点定出生辰与农历。hour 为 None 表示时辰未知（默认午时占位）。"""
    warnings = []
    clock_known = hour is not None
    solar_input = birth_solar
    if clock_known:
        shichen_i = ((hour + 1) // 2) % 12
        hour_zhi = ZHI[shichen_i]
        # 晚子时归属：仅农历「日」进位，输入日期本身不变
        solar_date = birth_solar
        if hour == 23 and late_zishi == "next-day":
            solar_date = birth_solar + timedelta(days=1)
            warnings.append("晚子时（23:00 后）：农历日按次日计（可用 --late-zishi same-day 改回）")
    else:
        hour_zhi = "午"
        solar_date = birth_solar
        warnings.append("时辰未知，已按午时占位；时系诸星（昌曲、空劫、火铃、台辅封诰）不可用")

    ly, lm, ld, leap = solar_to_lunar(solar_date.year, solar_date.month, solar_date.day)
    if shuo_near_midnight(solar_date.year, solar_date.month, solar_date.day):
        warnings.append("该日朔落在子夜附近，农历换算可能与官方历书差一日，建议用权威农历工具复核")

    # 生月修正（闰月）
    month_num = lm
    if leap:
        if leap_policy == "next-month":
            month_num = lm + 1 if lm < 12 else 1
            warnings.append("闰%s生：按《全书》作下一月（%s）起安身命"
                            % (LUNAR_MONTH_NAMES[lm], LUNAR_MONTH_NAMES[month_num]))
        else:
            if ld <= 15:
                month_num = lm
            else:
                month_num = lm + 1 if lm < 12 else 1
            warnings.append("闰%s生：按分半法（前十五日作本月，后十五日作下一月）"
                            % LUNAR_MONTH_NAMES[lm])

    # 年干支（立春分界）
    _, year_gan, year_zhi = year_gz_of(
        beijing(solar_date.year, solar_date.month, solar_date.day, hour or 12, minute or 0),
        year_divide)

    # 命宫 / 身宫
    month_idx = (month_num - 1) % 12           # 寅=0
    tsteps = ZHI.index(hour_zhi)
    ming_pos = (month_idx - tsteps) % 12
    shen_pos = (month_idx + tsteps) % 12
    ming_zhi = pan_to_zhi(ming_pos)
    shen_zhi = pan_to_zhi(shen_pos)

    return {
        "solar_date": solar_date,
        "solar_input": solar_input,
        "lunar": (ly, lm, ld, leap),
        "month_num": month_num,
        "day_num": ld,
        "hour_zhi": hour_zhi,
        "hour": hour,
        "minute": minute,
        "clock_known": clock_known,
        "year_gan": year_gan,
        "year_zhi": year_zhi,
        "ming_zhi": ming_zhi,
        "shen_zhi": shen_zhi,
        "sex": sex,
        "warnings": warnings,
    }


def apply_true_solar(birth_solar, hour, minute, longitude, warnings):
    """依经度与均时差把钟表时换算为真太阳时。

    返回 (新日期, 新时, 新分, 校正量分钟)。hour 为 None（时辰未知）时原样返回。
    同时把校正结果与「是否跨时辰」写入 warnings。
    """
    if longitude is None or hour is None:
        return birth_solar, hour, minute, None

    shift = true_solar_shift_minutes(longitude, birth_solar.year,
                                     birth_solar.month, birth_solar.day, hour)
    total = hour * 60 + (minute or 0) + shift
    day_delta, rem = divmod(int(round(total)), 1440)
    new_date = birth_solar + timedelta(days=day_delta)
    new_hour, new_minute = divmod(rem, 60)

    old_zhi = ZHI[((hour + 1) // 2) % 12]
    new_zhi = ZHI[((new_hour + 1) // 2) % 12]

    warnings.append(
        "真太阳时校正：东经%.4f°（相对120°E %+.1f分）＋均时差%+.1f分＝%+.1f分；"
        "钟表时 %02d:%02d → 真太阳时 %02d:%02d"
        % (longitude, (float(longitude) - 120.0) * 4.0,
           equation_of_time_minutes(birth_solar.year, birth_solar.month, birth_solar.day, hour),
           shift, hour, minute or 0, new_hour, new_minute))

    if old_zhi != new_zhi:
        warnings.append(
            "★ 校正后跨时辰：%s时 → %s时。全盘命身宫、五行局、紫微与安星俱变，"
            "请以真太阳时为准重排（本脚本已按真太阳时排定）" % (old_zhi, new_zhi))
    else:
        warnings.append("校正后时辰不变（仍为%s时），盘面不需重排" % new_zhi)

    # 接近时辰边界提示（距边界 15 分内）
    m = new_hour * 60 + new_minute
    for bound in (60 * 23 + 0, 60 * 1, 60 * 3, 60 * 5, 60 * 7, 60 * 9,
                  60 * 11, 60 * 13, 60 * 15, 60 * 17, 60 * 19, 60 * 21, 60 * 23):
        if abs(m - bound) <= 15:
            warnings.append("真太阳时距时辰边界（%02d:00）仅 %d 分，生时须格外复核——"
                            "原书云「若差讹则命不准矣」" % (bound // 60, abs(m - bound)))
            break

    return new_date, new_hour, new_minute, shift


def build(birth_solar, hour=None, minute=None, shichen=None, sex="男",
          place=None, leap_policy="next-month", late_zishi="next-day",
          daxian_convention="quanshu", target_year=None, deceased_year=None,
          year_divide="exact", now=None, longitude=None, true_solar=True):
    if hour is None and shichen:
        hour, minute = SHICHEN_MID[shichen]
    elif hour is None:
        pass  # 时辰未知
    if minute is None:
        minute = 0

    warnings = []
    if longitude is not None and hour is not None and true_solar:
        birth_solar, hour, minute, _ = apply_true_solar(
            birth_solar, hour, minute, longitude, warnings)

    info = resolve(birth_solar, hour, minute, sex, leap_policy, late_zishi, year_divide)
    warnings.extend(info["warnings"])

    is_male = sex == "男"
    is_yang = GAN.index(info["year_gan"]) % 2 == 0

    board, meta = stars_by_branch(
        info["ming_zhi"], info["shen_zhi"], info["year_gan"], info["year_zhi"],
        info["month_num"], info["day_num"], info["hour_zhi"], is_yang, is_male)
    meta["ming_zhi"] = info["ming_zhi"]

    # 旬中空亡（依年柱旬首）
    apply_xunkong(board, info["year_gan"], info["year_zhi"])

    palaces = build_palaces(info["ming_zhi"], board, meta, info["year_gan"],
                            info["year_zhi"], is_yang, is_male)

    yun = compute(info["lunar"][0], info["month_num"], info["day_num"], info["hour_zhi"],
                  is_male, info["year_gan"], info["year_zhi"], board, meta)

    if now is None:
        now = datetime.now(BJ)
    current_year = int(target_year) if target_year else now.year
    if deceased_year is not None:
        current_year = min(current_year, int(deceased_year))
    age = current_year - info["solar_date"].year + 1
    dx_used = yun["daxian"] if daxian_convention == "quanshu" else yun["daxian_common"]
    cur_dx = age_at(dx_used, age)
    cur_xx = xiaoxian_at(yun["xiaoxian"], age)

    # 本命命宫星曜（解灾检查用）
    ming_stars = [s[0] for s in board[info["ming_zhi"]] if s[0] in MAJOR_STARS]

    return {
        "info": info,
        "meta": meta,
        "palaces": palaces,
        "yun": yun,
        "board": board,
        "current_year": current_year,
        "age": age,
        "cur_daxian": cur_dx,
        "cur_xiaoxian": cur_xx,
        "current_gz": liunian_gz(current_year),
        "warnings": warnings,
        "place": place,
        "sex": sex,
        "daxian_convention": daxian_convention,
        "ming_stars": ming_stars,
    }


def _fmt_star(s):
    star, b, m = s
    txt = star
    if b:
        txt += "(%s)" % b
    if m:
        txt += "·%s" % m
    return txt


def palace_label(name):
    """宫名统一加「宫」后缀（命宫除外）。"""
    return "命宫" if name == "命宫" else name + "宫"


def format_report(r):
    info = r["info"]
    meta = r["meta"]
    ly, lm, ld, leap = info["lunar"]
    si = info.get("solar_input", info["solar_date"])
    lines = []
    lines.append("## 输入")
    si = info.get("solar_input", info["solar_date"])
    lines.append("- 阳历：%04d-%02d-%02d%s" % (
        si.year, si.month, si.day,
        "" if not info["clock_known"] else " %02d:%02d" % (info["hour"], info["minute"])))
    lines.append("- 农历：%s" % format_lunar(ly, lm, ld, leap))
    lines.append("- 时辰：%s" % info["hour_zhi"])
    lines.append("- 性别：%s" % r["sex"])
    if r["place"]:
        lines.append("- 出生地：%s" % r["place"])
    lines.append("")
    lines.append("## 命身与局")
    lines.append("- 年干支：%s%s（立春分界）" % (info["year_gan"], info["year_zhi"]))
    lines.append("- 命宫：%s%s" % (meta["ming_gan"], info["ming_zhi"]))
    lines.append("- 身宫：%s" % info["shen_zhi"])
    lines.append("- 五行局：%s（局数 %d，即大限起始岁）" % (JU_NAME[meta["ju"]], meta["ju"]))
    lines.append("- 命主：%s ／ 身主：%s" % (
        SOUL_STAR[info["ming_zhi"]], BODY_STAR[info["year_zhi"]]))
    lines.append("- 紫微：%s ／ 天府：%s" % (meta["ziwei_zhi"], meta["tianfu_zhi"]))
    lines.append("")
    lines.append("## 十二宫")
    lines.append("| 宫位 | 干支 | 星曜（庙陷·四化） |")
    lines.append("|---|---|---|")
    for p in r["palaces"]:
        ss = "、".join(_fmt_star(s) for s in p["stars"]) or "—"
        mark = "★" if p["zhi"] == info["ming_zhi"] else ("☆" if p["zhi"] == info["shen_zhi"] else "")
        lines.append("| %s%s | %s%s | %s |" % (p["name"], mark, p["gan"], p["zhi"], ss))
    lines.append("## 四化（生年干 %s）" % info["year_gan"])
    lx, qx, kx, jx = meta["mutagen"]
    for label, star in (("化禄", lx), ("化权", qx), ("化科", kx), ("化忌", jx)):
        where = [p["name"] for p in r["palaces"]
                 if any(s[0] == star for s in p["stars"])]
        lines.append("- %s：%s（%s）" % (label, star, "、".join(where) or "不在盘上"))
    lines.append("")
    lines.append("## 大限（%s）" % ("《全书》自父母宫起顺行/兄弟宫起逆行"
                                  if r["daxian_convention"] == "quanshu"
                                  else "自命宫起"))
    for row in (r["yun"]["daxian"] if r["daxian_convention"] == "quanshu" else r["yun"]["daxian_common"]):
        lo, hi = row["range"]
        mark = " ← 当前" if r["cur_daxian"] and r["cur_daxian"]["zhi"] == row["zhi"] and row["range"] == tuple(r["cur_daxian"]["range"]) else ""
        lines.append("- %d-%d 岁：%s（%s）%s" % (lo, hi, row["zhi"], palace_label(row["palace"]), mark))
    lines.append("")
    lines.append("## 小限（男顺女逆，生年支 %s 起 %s）"
                 % (info["year_zhi"], XIAOXIAN_START[info["year_zhi"]]))
    for row in r["yun"]["xiaoxian"]:
        ages = row["ages"]
        mark = " ← 当前（%d岁）" % r["age"] if r["age"] in ages else ""
        lines.append("- %s（%s）：%s 岁%s" % (row["zhi"], palace_label(row["palace"]),
                                             "、".join(str(a) for a in ages), mark))
    lines.append("")
    lines.append("## 童限（局数前之过渡）")
    lines.append("- " + "；".join("%d岁%s" % (t["age"], t["palace"]) for t in r["yun"]["tonglian"]))
    lines.append("")
    lines.append("## 当前运限")
    lines.append("- 断事年份：%d 年（%s），虚岁 %d" % (r["current_year"], r["current_gz"], r["age"]))
    if r["cur_daxian"]:
        lo, hi = r["cur_daxian"]["range"]
        lines.append("- 大限：%d-%d 岁 行 %s（%s）" % (lo, hi, r["cur_daxian"]["zhi"],
                                                    palace_label(r["cur_daxian"]["palace"])))
    if r["cur_xiaoxian"]:
        lines.append("- 小限：行 %s（%s）" % (r["cur_xiaoxian"]["zhi"],
                                           palace_label(r["cur_xiaoxian"]["palace"])))
    # 应期（南北斗）
    is_yang = GAN.index(info["year_gan"]) % 2 == 0
    is_male = r["sex"] == "男"
    # 《全书》卷三：阳男阴女南斗为福（下五年/下半年）；阴男阳女北斗为福（上五年/上半年）
    if (is_yang and is_male) or ((not is_yang) and (not is_male)):
        lines.append("- 南北斗应期：南斗为福（大限断下五年、小限断下半年）")
    else:
        lines.append("- 南北斗应期：北斗为福（大限断上五年、小限断上半年）")
    lines.append("- 十二支所忌：%s" % ZHI_TABOO[info["year_zhi"]])
    nayin_name, nayin_wx = nayin_of(meta["ming_gan"], info["ming_zhi"])
    gua, zhis = NAYIN_TABOO[nayin_wx]
    lines.append("- 纳音忌宫：命宫纳音「%s」属%s，忌 %s（%s）——「纵然吉曜相逢照，未免官灾闹一场」"
                 % (nayin_name, nayin_wx, gua, zhis))
    ming_major = r["ming_stars"]
    if ming_major:
        solve = [s for s in ming_major if s in SOLVE_JIAXIAN]
        lines.append("- 解灾检查：命宫主星 %s%s" % (
            "、".join(ming_major),
            "（%s 在命，可解羊陀夹限）" % "、".join(solve) if solve else "（不在解灾四星内，逢夹限须谨慎）"))
    lines.append("")
    lines.append("## 警告")
    if r["warnings"]:
        seen = set()
        for w in r["warnings"]:
            if w in seen:
                continue
            seen.add(w)
            lines.append("- %s" % w)
    else:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_iso_date(text, flag):
    try:
        parts = text.split("-")
        if len(parts) != 3:
            raise ValueError
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        raise argparse.ArgumentTypeError("%s 需要 YYYY-MM-DD，收到 %r" % (flag, text))


def parse_hour(text):
    try:
        hh, mm = text.split(":")
        h, m = int(hh), int(mm)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h, m
    except ValueError:
        raise argparse.ArgumentTypeError("--hour 需要 HH:MM，收到 %r" % text)


def build_parser():
    p = argparse.ArgumentParser(
        description="紫微斗数排盘（《紫微斗数全书》安星诀，北京时间，无第三方依赖）")
    p.add_argument("--solar", help="阳历 YYYY-MM-DD")
    p.add_argument("--lunar", help="农历 YYYY-MM-DD（年-月-日数字）")
    p.add_argument("--leap", action="store_true", help="农历闰月")
    p.add_argument("--hour", help="出生钟点 HH:MM（北京时间），与 --shichen 互斥")
    p.add_argument("--shichen", choices=list(ZHI), help="时辰地支")
    p.add_argument("--sex", required=True, choices=("男", "女"), help="性别（必填）")
    p.add_argument("--place", help="出生地（仅展示）")
    p.add_argument("--longitude", type=float, help="出生地东经（度，正为东经）。"
                   "给出后自动把 --hour 从钟表时换算为真太阳时再定时辰；"
                   "不给出则按钟表时直接定时辰（会有跨时辰误差风险）")
    p.add_argument("--no-true-solar", action="store_false", dest="true_solar",
                   default=True,
                   help="关闭真太阳时校正，直接按钟表时定时辰（与不做校正的外部软体对齐）")
    p.add_argument("--leap-policy", choices=("next-month", "split15"),
                   default="next-month", dest="leap_policy",
                   help="闰月处理：next-month=全书作下一月（默认）；split15=前十五日作本月")
    p.add_argument("--late-zishi", choices=("next-day", "same-day"),
                   default="next-day", dest="late_zishi",
                   help="晚子时（23:00 后）归属，默认次日")
    p.add_argument("--daxian", choices=("quanshu", "common"), default="quanshu",
                   help="大限起宫：quanshu=全书自父母/兄弟宫（默认）；common=自命宫")
    p.add_argument("--year-divide", choices=("exact", "day"), default="exact",
                   dest="year_divide",
                   help="年柱分界：exact=立春精确时刻（默认，与八字同口径）；"
                        "day=立春当日即算新年（与部分斗数软体对齐）")
    p.add_argument("--year", type=int, dest="target_year", help="要断的年份（默认今年）")
    p.add_argument("--deceased-year", type=int, dest="deceased_year",
                   help="已故年份，运限只列到该年之前")
    # ---- 输出格式 ----
    p.add_argument("--format", choices=("html", "md", "both"), default="html",
                   dest="fmt",
                   help="输出格式：html=完整命盘页面（默认，写入文件）；"
                        "md=markdown 文本（stdout）；both=两者都出")
    p.add_argument("--out", dest="out", help="HTML 输出路径（默认按命主命名写到当前目录）")
    p.add_argument("--interpret", dest="interpret",
                   help="判读 markdown 文件路径，按 `## 标题` 分节注入 HTML 的判读区")
    p.add_argument("--stdout-html", action="store_true", dest="stdout_html",
                   help="把 HTML 写到 stdout 而非文件（不落盘）")
    p.add_argument("--title", dest="title", help="HTML 页面标题（默认自动生成）")
    return p


def run(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.solar and not args.lunar:
        parser.error("至少提供 --solar 或 --lunar")
    if args.hour and args.shichen:
        parser.error("--hour 与 --shichen 互斥")
    if args.leap and not args.lunar:
        parser.error("--leap 只能与 --lunar 同时使用")

    hour = minute = None
    if args.hour:
        hour, minute = parse_hour(args.hour)

    solar_date = None
    lunar_arg = None
    if args.solar:
        solar_date = parse_iso_date(args.solar, "--solar")
    if args.lunar:
        lunar_arg = parse_iso_date(args.lunar, "--lunar")
        try:
            conv = lunar_to_solar(lunar_arg.year, lunar_arg.month, lunar_arg.day, leap=args.leap)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if solar_date is None:
            solar_date = conv

    try:
        result = build(solar_date, hour=hour, minute=minute, shichen=args.shichen,
                       sex=args.sex, place=args.place, leap_policy=args.leap_policy,
                       late_zishi=args.late_zishi, daxian_convention=args.daxian,
                       longitude=args.longitude, true_solar=args.true_solar,
                       year_divide=args.year_divide,
                       target_year=args.target_year, deceased_year=args.deceased_year)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    # 仅农历输入时展示用户所给的农历
    if lunar_arg and not args.solar:
        result["info"]["lunar"] = (lunar_arg.year, lunar_arg.month, lunar_arg.day, args.leap)

    report = format_report(result)

    # ---------------- markdown 输出 ----------------
    if args.fmt in ("md", "both"):
        sys.stdout.write(report)
        if not report.endswith("\n"):
            sys.stdout.write("\n")

    # ---------------- HTML 输出 ----------------
    if args.fmt in ("html", "both"):
        try:
            import ziwei_html
        except ImportError:
            _here = os.path.dirname(os.path.abspath(__file__))
            if _here not in sys.path:
                sys.path.insert(0, _here)
            import ziwei_html

        interp = None
        if args.interpret:
            if not os.path.exists(args.interpret):
                print("判读文件不存在：%s" % args.interpret, file=sys.stderr)
                return 2
            with open(args.interpret, "r", encoding="utf-8") as fh:
                interp = ziwei_html.parse_interpret(fh.read())
            if not interp:
                print("提示：判读文件中未识别到任何 `## 标题` 分节，"
                      "HTML 判读区将留空。可用的标题见 SKILL.md。", file=sys.stderr)

        html = ziwei_html.render_html(result, interpret=interp)
        if args.title:
            html = re.sub(r"<title>.*?</title>",
                          "<title>%s</title>" % args.title.replace("&", "&amp;")
                          .replace("<", "&lt;"), html, count=1, flags=re.S)

        if args.stdout_html:
            sys.stdout.write(html)
            if not html.endswith("\n"):
                sys.stdout.write("\n")
        else:
            out_path = args.out or default_html_name(result)
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(html)
            print("HTML 已生成：%s（%.1f KB）"
                  % (os.path.abspath(out_path), len(html.encode("utf-8")) / 1024.0),
                  file=sys.stderr)
            if interp is None:
                print("提示：未传入 --interpret，判读区为空占位。"
                      "建议撰写判读 markdown 后用 --interpret 注入，"
                      "或直接编辑 HTML 的判读区。", file=sys.stderr)
    return 0


def default_html_name(result):
    """默认输出文件名：紫微斗数命盘_<年干支>年<农历月><农历日><时辰>.html

    例：紫微斗数命盘_甲戌年六月二十午时.html
    """
    import ziwei_html
    info = result["info"]
    ly, lm, ld, leap = info["lunar"]
    return "紫微斗数命盘_%s年%s%s月%s%s时.html" % (
        info["year_gan"] + info["year_zhi"],
        "闰" if leap else "", ziwei_html.format_lunar_month(lm),
        ziwei_html.format_lunar_num(ld),
        info["hour_zhi"])


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
