![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![WorkBuddy](https://img.shields.io/badge/WorkBuddy-Skill-blueviolet)
![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)
![Python](https://img.shields.io/badge/Python-Stdlib%20Only-3776AB)

# 紫微斗数全书 Skill

以明刊本《紫微斗数全书》（托名宋·陈抟，明·罗洪先序，嘉靖庚戌 1550）为判读根基的紫微斗数排盘与判盘工具。
通过交互式对话收集出生信息，用**零依赖排盘脚本**排出十二宫盘，再依《全书》原本次第做综合判盘。

## 功能

- **信息收集** — 逐步收集姓名、阳历/农历生日、出生时辰、性别、出生地等信息
- **排盘计算** — 安身命、定十二宫、起五行局、起紫微天府、布十四主星与诸星、四化、庙旺落陷、大限小限童限、流年（脚本一次算全）
- **综合判盘** — 按《全书》次第九步：命身 → 三方四正庙陷 → 四化 → 八座福德 → 男女分叉 → 十二宫 → 格局 → 运限 → 历史校准

## 安装

> **注意**：WorkBuddy 从 skills 目录查找 skill，请在正确的位置执行。本机需已安装 `python3`（3.6+，只用标准库，**无需 pip 安装任何第三方包**）。

```bash
# 安装到全局（所有项目都能用）
git clone https://github.com/leeseangm-dot/ziwei-quanshu.git ~/.workbuddy/skills/ziwei-quanshu

# 或安装到当前项目（项目级，团队共享）
mkdir -p .workbuddy/skills
git clone https://github.com/leeseangm-dot/ziwei-quanshu.git .workbuddy/skills/ziwei-quanshu
```

## 使用

在 WorkBuddy 中输入以下任意关键词即可触发：

`紫微斗数` `紫微` `斗数` `紫微命盘` `排紫微盘` `看紫微` `命宫` `身宫` `十二宫` `四化` `庙旺落陷` `大限流年` `ziwei`

触发后，Skill 会逐步引导你提供出生信息，然后调用本仓库的排盘脚本并做综合分析。确认出生信息后会执行：

```bash
python3 scripts/ziwei_pan.py --solar 1990-05-15 --shichen 午 --sex 男
```

其余等价调用：

```bash
python3 scripts/ziwei_pan.py --solar 1990-05-15 --hour 12:00 --sex 男   # 用时刻
python3 scripts/ziwei_pan.py --lunar 1990-04-21 --shichen 午 --sex 男   # 用农历
python3 scripts/ziwei_pan.py --lunar 2020-04-01 --leap --hour 12:00 --sex 女  # 农历闰月
```

### 主要参数

| 参数 | 说明 |
|---|---|
| `--solar YYYY-MM-DD` | 阳历生日 |
| `--lunar YYYY-MM-DD` | 农历生日（年-月-日数字） |
| `--leap` | 农历闰月 |
| `--hour HH:MM` / `--shichen 子..亥` | 出生时刻（互斥；都不传则时辰未知） |
| `--sex 男\|女` | **必填** |
| `--year YYYY` | 断事年份（默认当年） |
| `--daxian quanshu\|common` | 大限起宫（默认 `quanshu`，依《全书》） |
| `--leap-policy next-month\|split15` | 闰月口径（默认 `next-month`，依《全书》） |
| `--year-divide exact\|day` | 年柱分界（默认 `exact`，立春精确时刻） |
| `--late-zishi next-day\|same-day` | 晚子时归属（默认 `next-day`） |

### 三处流派分歧

紫微斗数有三处注家各异的判法，本脚本一律**默认《全书》口径**，另留开关以便与外部软体对齐：

| 分歧点 | 《全书》口径（默认） | 通行做法 | 开关 |
|---|---|---|---|
| 大限起宫 | 自命宫起 | 自命宫起（部分流派自身宫） | `--daxian` |
| 闰月安命 | 闰月作下月论 | 闰月分半（前半月作本月、后半月作下月） | `--leap-policy` |
| 年柱分界 | 立春**精确时刻** | 立春**当日**即换 | `--year-divide` |

> 与外部排盘软体（iztro 等）对盘时需同时切换三个开关，否则盘会整体错位：
> ```bash
> python3 scripts/ziwei_pan.py --solar 1990-05-15 --hour 12:00 --sex 男 \
>     --daxian common --leap-policy split15 --year-divide day
> ```

## 参考典籍

| 典籍 | 用途 |
|------|------|
| 《紫微斗数全书》太微赋·形性赋 | 论星性本源、总纲 |
| 《紫微斗数全书》斗数准绳·发微论 | 论星垣、立命之要 |
| 《紫微斗数全书》诸星问答论 | 论十四主星、辅煞诸星性情 |
| 《紫微斗数全书》骨髓赋（男/女） | 论格局与命格高下 |
| 《紫微斗数全书》安星诀 | 论安身命、起紫微、安诸星 |
| 《紫微斗数全书》十二宫论断 | 论十二宫分司所宜 |
| 《斗数宣微》 | 旁参，论星曜互涉 |
| 《十八飞星策天紫微斗数》 | 旁参，论古法飞星 |

## 项目结构

```
ziwei-quanshu/
├── SKILL.md                        # Skill 入口（三阶段工作流 + 核心框架）
├── scripts/
│   ├── ziwei_pan.py                #   排盘脚本（标准库，无 pip 依赖）
│   └── test_ziwei_pan.py           #   回归测试 + 外部库交叉对照
├── references/
│   └── paipan-rules.md             #   排盘规则速查（与脚本同口径）
├── chapters/                       #   16 章原书提炼
│   ├── ch01-xu-yu-zonggang.md      #     罗序与太微赋
│   ├── ch02-xingxing-fu.md         #     形性赋
│   ├── ch03-zhunsheng-fawei.md     #     星垣论·斗数准绳·发微论
│   ├── ch04-zhuxing-wenda.md       #     诸星问答论（上）
│   ├── ch05-fuxing-sihua-shaxing.md#     诸星问答论（下）
│   ├── ch06-gusui-fu.md            #     斗数骨髓赋
│   ├── ch07-nvming-gusui.md        #     女命骨髓赋
│   ├── ch08-geju-lun.md            #     格局论
│   ├── ch09-anshen-mingli.md       #     安身命例与起例总纲
│   ├── ch10-anxing-jue.md          #     安星诀总汇
│   ├── ch11-miaowang-wuxing.md     #     庙旺落陷与南北斗五行分属
│   ├── ch12-shiergong-shang.md     #     论十二宫（上）
│   ├── ch13-shiergong-xia.md       #     论十二宫（下）
│   ├── ch14-tanxing-yaolun.md      #     谈星要论与命格高下
│   ├── ch15-daxian-liunian.md      #     大限、小限与流年运限
│   └── ch16-zhuxing-tongyuan.md    #     诸星同垣各司所宜
├── glossary.md                     # 术语表
├── patterns.md                     # 判读模式
├── cheatsheet.md                   # 断命速查表
├── LICENSE
└── README.md
```

## 验证

```bash
python3 scripts/test_ziwei_pan.py            # 经典口诀锚点（105 项断言）
python3 scripts/test_ziwei_pan.py --cross    # 另加与外部排盘库的交叉对照
```

排盘算法以《全书》安星诀逐条实现，并用 1200+ 随机样本盘与外部独立排盘库（iztro）比对：
**命宫、身宫、五行局、紫微天府、十四主星逐一一致**。农历换算另与权威历法库
（lunar-javascript）对照 1500 日。

几处易错点已专门校准，详见 `references/paipan-rules.md`：

- 闰月判定的**日粒度**（朔与中气同日时最易错）
- 年柱分界的**时刻粒度**（立春当刻前后属不同年）
- 紫微定位的「商数宫前走，补数奇退偶进」

## 免责声明

本 Skill 仅供传统文化学习与娱乐参考，分析结果不构成任何决策依据。
命理学属于传统文化范畴，请理性看待。原著判词带有明代时代印记
（如对女性的贬抑表述、对「僧道」的贬损），本技能按原书保留以便研究，
**不代表当代价值判断**。
