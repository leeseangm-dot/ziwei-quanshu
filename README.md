![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)
![Python](https://img.shields.io/badge/Python-Stdlib%20Only-3776AB)
![Vendor](https://img.shields.io/badge/Vendor-Neutral-informational)

# 紫微斗数全书 Skill

以明刊本《紫微斗数全书》（托名宋·陈抟，明·罗洪先序，嘉靖庚戌 1550）为判读根基的紫微斗数排盘与判盘工具。
通过交互式对话收集出生信息，用**零依赖排盘脚本**排出十二宫盘，再依《全书》原本次第做综合判盘。

## 功能

- **信息收集** — 逐步收集姓名、阳历/农历生日、出生时辰、性别、出生地等信息
- **排盘计算** — 安身命、定十二宫、起五行局、起紫微天府、布十四主星与诸星、四化、庙旺落陷、大限小限童限、流年（脚本一次算全）
- **综合判盘** — 按《全书》次第九步：命身 → 三方四正庙陷 → 四化 → 八座福德 → 男女分叉 → 十二宫 → 格局 → 运限 → 历史校准
- **HTML 命盘** — **最终交付物是一个可直接打开、可打印成 PDF 的单文件 HTML 命盘**（非 markdown 文本）

## 交付物：HTML 命盘

命盘是 4×4 的空间结构，markdown 表格表达不了十二宫方位与三方四正，所以本技能
**默认产出 HTML 文件**。单文件、内嵌 CSS、无任何外部依赖，离线可用。

页面含：四化配色（禄红/权紫/科蓝/忌黑）、庙陷标注、大限岁数区间、当限高亮、
小限与童限表、当前运限，以及五个**判读槽位**（命身与格局 / 四化与生克 /
十二宫分述 / 运限推演 / 综合论断）。判读由模型撰写后按槽位注入，
使「脚本算准」与「模型读懂」解耦。

### 生成

不带 `--format` 时**默认输出 HTML**：

```bash
# 生成 紫微斗数命盘_甲戌年六月二十午时.html（写在当前目录）
python3 scripts/ziwei_pan.py --solar 1994-07-28 --shichen 午 --sex 男 --year 2026
```

### 注入判读

判读写成一个 markdown 文件，用 `## 标题` 分节（标题须与五个槽位名一致），
`--interpret` 注入：

```markdown
## 一、命身与格局
命宫**丁丑**坐天魁、陀罗……

## 二、四化与生克
- 廉贞化禄落官禄
- 太阳化忌落疾厄

## 三、十二宫分述
1. 命宫：……
```

```bash
python3 scripts/ziwei_pan.py --solar 1994-07-28 --shichen 午 --sex 男 \
    --interpret 判读.md --out 命盘.html
```

标题之外的散文会被忽略；未提供的槽位在页面上留「待补」占位。
支持 `**粗体**`、`[[高亮]]`、`[[g:绿色高亮]]`、无序/有序列表、`> 引用`（放原书判词）。

## 安装

本技能遵循 **Agent Skills 开放规范**（一个目录一个 skill，`SKILL.md` + YAML frontmatter +
可选 `scripts/` `references/`），因此**不绑定任何特定 AI 工具** —— 只要是能读取 skill 目录的
客户端都能用。

> 前置条件：本机已安装 `python3`（3.6+）。排盘脚本**只用标准库，无需 pip 安装任何第三方包**。

### 方式一：通用目录（推荐，多个工具共享同一份）

`.agents/skills/` 是跨客户端约定路径，Codex、Cursor、GitHub Copilot、Gemini CLI、
OpenCode、Amp、Kimi CLI、Replit 等均会扫描：

```bash
# 用户级（所有项目可用）
git clone https://github.com/leeseangm-dot/ziwei-quanshu.git ~/.agents/skills/ziwei-quanshu

# 项目级（随仓库提交，团队共享）
mkdir -p .agents/skills
git clone https://github.com/leeseangm-dot/ziwei-quanshu.git .agents/skills/ziwei-quanshu
```

### 方式二：各客户端专用目录

若所用工具只认自家目录，把仓库 clone 到对应位置即可（**内容无需任何改动**）：

| 客户端 | 用户级目录 | 项目级目录 |
|---|---|---|
| WorkBuddy | `~/.workbuddy/skills/` | `.workbuddy/skills/` |
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Codex | `~/.codex/skills/` | `.agents/skills/` |
| Cursor | `~/.cursor/skills/` | `.cursor/skills/` |
| GitHub Copilot | `~/.copilot/skills/` | `.github/skills/` |
| Gemini CLI | `~/.gemini/skills/` | `.gemini/skills/` |
| Cline / Roo Code | `~/.cline/skills/` | `.cline/skills/` |
| Trae / Trae CN | `~/.trae/skills/` | `.trae/skills/` |
| Qwen Code | `~/.qwen/skills/` | `.qwen/skills/` |

例（WorkBuddy）：

```bash
git clone https://github.com/leeseangm-dot/ziwei-quanshu.git ~/.workbuddy/skills/ziwei-quanshu
```

> **多工具共用**：若已按方式一装到 `~/.agents/skills/`，可用软链接让只认专用目录的工具也能发现，
> 避免维护多份副本：
> ```bash
> ln -s ~/.agents/skills/ziwei-quanshu ~/.workbuddy/skills/ziwei-quanshu   # macOS / Linux
> # Windows（管理员 PowerShell）：
> # New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.workbuddy\skills\ziwei-quanshu" `
> #   -Target "$env:USERPROFILE\.agents\skills\ziwei-quanshu"
> ```

### 方式三：无法识别 skill 的客户端

若所用工具不支持 skill 目录（如豆包等纯对话式产品），**脚本仍可独立使用** ——
排盘部分不依赖任何 AI，直接命令行调用即可：

```bash
git clone https://github.com/leeseangm-dot/ziwei-quanshu.git
cd ziwei-quanshu
# 直接得到 HTML 命盘文件
python3 scripts/ziwei_pan.py --solar 1990-05-15 --shichen 午 --sex 男
# 若该工具只能读文本，改用 md 输出，把内容贴过去
python3 scripts/ziwei_pan.py --solar 1990-05-15 --shichen 午 --sex 男 --format md
```

排盘部分不依赖任何 AI，在任何有 `python3` 的环境都能跑；生成的 HTML 命盘用浏览器
直接打开即可。知识库部分（`chapters/` `patterns.md` `cheatsheet.md`）是纯 Markdown，
也可直接作为参考资料投喂给该工具。

## 使用

在支持 skill 的客户端（WorkBuddy / Claude Code / Codex / Cursor 等）中输入以下任意关键词即可触发：

`紫微斗数` `紫微` `斗数` `紫微命盘` `排紫微盘` `看紫微` `命宫` `身宫` `十二宫` `四化` `庙旺落陷` `大限流年` `ziwei`

触发后，Skill 会逐步引导你提供出生信息，然后调用本仓库的排盘脚本并做综合分析。
确认出生信息后会执行（默认即产出 HTML 命盘）：

```bash
python3 scripts/ziwei_pan.py --solar 1990-05-15 --shichen 午 --sex 男
```

其余等价调用：

```bash
python3 scripts/ziwei_pan.py --solar 1990-05-15 --hour 12:00 --sex 男   # 用时刻
python3 scripts/ziwei_pan.py --lunar 1990-04-21 --shichen 午 --sex 男   # 用农历
python3 scripts/ziwei_pan.py --lunar 2020-04-01 --leap --hour 12:00 --sex 女  # 农历闰月
python3 scripts/ziwei_pan.py --solar 1990-05-15 --shichen 午 --sex 男 --format md  # 只要文本
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
| `--format html\|md\|both` | 输出格式（**默认 `html`**；`md` 打到 stdout） |
| `--out <路径>` | HTML 输出路径（默认按命主自动命名） |
| `--interpret <判读.md>` | 把判读 markdown 按槽位注入 HTML |
| `--stdout-html` | HTML 打到 stdout 而非写文件 |
| `--title "…"` | HTML 页面标题（默认自动生成） |

**输出模式**：`html`（默认，写文件）/ `md`（stdout 文本）/ `both`。
进度提示与警告走 stderr，HTML 不混入 stdout，可安全重定向。

### 三处流派分歧

紫微斗数有三处注家各异的判法，本脚本一律**默认《全书》口径**，另留开关以便与外部软体对齐：

| 分歧点 | 《全书》口径（默认） | 通行做法 | 开关 |
|---|---|---|---|
| 大限起宫 | 阳男阴女起**父母宫**顺行；阴男阳女起**兄弟宫**逆行 | 多数排盘软体自**命宫**起 | `--daxian` |
| 闰月安命 | 闰月作**下一月**论 | 闰月**分半**（前半月作本月、后半月作下月） | `--leap-policy` |
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
│   ├── ziwei_pan.py                #   排盘脚本（标准库，无 pip 依赖；默认产出 HTML）
│   ├── ziwei_html.py               #   HTML 命盘渲染器（零依赖）
│   ├── test_ziwei_pan.py           #   排盘回归测试 + 外部库交叉对照
│   └── test_ziwei_html.py          #   HTML 渲染回归测试
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
python3 scripts/test_ziwei_pan.py            # 经典口诀锚点（116 项断言）
python3 scripts/test_ziwei_pan.py --cross    # 另加与外部排盘库的交叉对照
python3 scripts/test_ziwei_html.py           # HTML 渲染回归（184 项断言）
```

`test_ziwei_html.py` 覆盖：4×4 宫格方位、十二宫齐全、主星/辅佐/杂曜分级、
庙陷与四化标记、判读槽位解析与注入、markdown→HTML 转义、渲染确定性、
无外部资源（离线可用）、农历月/日中文写法，以及 **md 文本 ↔ HTML 命盘一致性**。

排盘算法以《全书》安星诀逐条实现，并用 1200+ 随机样本盘与外部独立排盘库（iztro）比对：
**命宫、身宫、五行局、紫微天府、十四主星逐一一致**。农历换算另与权威历法库
（lunar-javascript）对照 1500 日。

HTML 渲染另与手写参考盘逐宫比对：**十二宫星曜全部覆盖**（参考盘省略的长生十二神、
博士十二神与部分杂曜，脚本补全并已逐项核算）。

几处易错点已专门校准，详见 `references/paipan-rules.md`：

- 闰月判定的**日粒度**（朔与中气同日时最易错）
- 年柱分界的**时刻粒度**（立春当刻前后属不同年）
- 紫微定位的「商数宫前走，补数奇退偶进」
- 南北斗应期按**阳男阴女／阴男阳女**配对（同性为南斗，异性为北斗），非按男女单边

## 免责声明

本 Skill 仅供传统文化学习与娱乐参考，分析结果不构成任何决策依据。
命理学属于传统文化范畴，请理性看待。原著判词带有明代时代印记
（如对女性的贬抑表述、对「僧道」的贬损），本技能按原书保留以便研究，
**不代表当代价值判断**。
