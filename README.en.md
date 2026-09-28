![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)
![Python](https://img.shields.io/badge/Python-Stdlib%20Only-3776AB)
![Vendor](https://img.shields.io/badge/Vendor-Neutral-informational)

[中文](README.md) | **English**

# Zi Wei Dou Shu (紫微斗数) Skill

A charting and interpretation tool for *Zi Wei Dou Shu* — Purple Star Astrology — grounded in the
Ming-dynasty woodblock edition of the **《紫微斗数全书》** (*Zi Wei Dou Shu Quan Shu*, "Complete Book
of Purple Star Astrology"; attributed to Chen Tuan 陈抟 of the Song, prefaced by Luo Hongxian 罗洪先,
1550). Birth data is collected through interactive dialogue, a **zero-dependency script** casts the
twelve-palace chart, and interpretation follows the original book's own sequence.

> **Note on terminology**: this README keeps Chinese terms for the astrology concepts
> (palace names, star names, chart rules) because they have no settled English equivalents —
> translating them would make the documentation harder to match against the source text.
> Romanization is given in parentheses where helpful.

## Features

- **Data collection** — interactively gathers name, solar/lunar birth date, birth hour, sex and birthplace
- **True solar time correction** — converts **clock time to true solar time** using longitude and the
  equation of time before fixing the birth hour, so people born in western China don't get an
  off-by-one *shichen* (时辰, two-hour period). See below
- **Chart casting** — *an shen ming* (安身命, locating the Life and Body palaces), the twelve palaces,
  the Five-Element Bureau (五行局), Zi Wei / Tian Fu (紫微／天府), the fourteen major stars (十四主星)
  and all subsidiary stars, the Four Transformations (四化), temple/bright and fallen states
  (庙旺落陷), major limits / minor limits / childhood limits (大限／小限／童限), and annual fortune
  (流年) — all computed in one pass
- **Interpretation** — follows the book's nine-step order: Life/Body palaces → 三方四正 and temple
  states → Four Transformations → 八座 screening and the Fu De palace → male/female divergence →
  the twelve palaces → pattern identification (格局) → cyclic limits → historical calibration
- **HTML chart** — **the final deliverable is a single-file HTML chart** that can be opened directly
  and printed to PDF (not a markdown report)

## True solar time correction

**Clock time (Beijing time) is not true solar time.** Beijing time is based on 120°E, while western
China spans much greater longitudes. Fixing the birth *shichen* from clock time makes **charts for
western-born people land one shichen off** — and the source text is explicit: 「若差讹则命不准矣」
("if it errs, the fate is not accurate"). A wrong hour changes the Life palace, Body palace,
Five-Element Bureau, Zi Wei position and every star placement.

```
total correction (min) = (birthplace longitude − 120) × 4 + equation of time
true solar time        = clock time + total correction
```

- **Longitude term**: 4 minutes per degree. Shanghai ~121°E → +4 min (negligible);
  Beijing ~116.4°E → −14 min; Chengdu ~104.1°E → −64 min; Kunming ~102.7°E → −69 min;
  Ürümqi ~87.6°E → −130 min.
- **Equation of time (EoT)**: caused by Earth's orbital eccentricity and the obliquity of the
  ecliptic; swings between −14 and +16 minutes over the year (NOAA simplified formula,
  accuracy about ±0.5 min).

Pass the birthplace longitude and the correction is applied automatically:

```bash
# Chengdu (~104.07°E)
# clock 13:30 (wei hour) -> true solar 12:20 (wu hour) -- crosses a shichen
python3 scripts/ziwei_pan.py --lunar 1994-06-20 --hour 13:30 --sex 男 --longitude 104.066

# disable the correction, to match external software that skips it
python3 scripts/ziwei_pan.py --lunar 1994-06-20 --hour 13:30 --sex 男 \
    --longitude 104.066 --no-true-solar
```

The script writes its working into `## 警告` (warnings): the correction breakdown, **whether a
shichen boundary was crossed**, and whether the result lands within 15 minutes of a boundary.
Day rollover is handled too (e.g. Ürümqi 00:30 → 22:14 of the previous day, with the lunar day
stepping back accordingly).

## Deliverable: the HTML chart

A chart is a 4×4 spatial structure — a markdown table cannot express the twelve-palace positions
or the 三方四正 relationships. So the skill **produces an HTML file by default**: a single file,
inline CSS, no external dependencies, usable offline.

The page contains: colour-coded Four Transformations (Lu red / Quan purple / Ke blue / Ji black),
temple-state annotations, major-limit age ranges, current-limit highlighting, minor-limit and
childhood-limit tables, the current cyclic-limit summary, and five **interpretation slots**
(Life/Body & patterns / Four Transformations & interactions / the twelve palaces / cyclic limits /
overall verdict). Interpretations are written by the model and injected into these slots,
decoupling "the script computes correctly" from "the model reads correctly".

### Generating

Without `--format`, the default output is **HTML**:

```bash
# writes 紫微斗数命盘_甲戌年六月二十午时.html into the current directory
python3 scripts/ziwei_pan.py --solar 1994-07-28 --shichen 午 --sex 男 --year 2026
```

### Injecting an interpretation

Write the interpretation as a markdown file, sectioned with `## headings` (headings must match the
five slot names), then inject it with `--interpret`:

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

Prose outside the headings is ignored; slots you don't supply get a "to be filled" placeholder.
Inline formatting supports `**bold**`, `[[highlight]]`, `[[g:green highlight]]`, bullet and
numbered lists, and `> quotes` (for quoting the source text).

## Installation

This skill follows the **Agent Skills open specification** (one directory per skill, `SKILL.md` +
YAML frontmatter + optional `scripts/` / `references/`). It is therefore **not tied to any specific
AI tool** — any client that can read a skill directory will work.

> Prerequisite: `python3` (3.6+) on your machine. The charting script uses the **standard library
> only — no pip packages needed**.

### Option 1: the common directory (recommended; share one copy across tools)

`.agents/skills/` is the cross-client convention path, scanned by Codex, Cursor, GitHub Copilot,
Gemini CLI, OpenCode, Amp, Kimi CLI, Replit and others:

```bash
# user level (available to all projects)
git clone https://github.com/leeseangm-dot/ziwei-quanshu.git ~/.agents/skills/ziwei-quanshu

# project level (committed with the repo, shared by the team)
mkdir -p .agents/skills
git clone https://github.com/leeseangm-dot/ziwei-quanshu.git .agents/skills/ziwei-quanshu
```

### Option 2: per-client directories

If your tool only scans its own directory, clone the repo there (**no content changes needed**):

| Client | User-level directory | Project-level directory |
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

Example (WorkBuddy):

```bash
git clone https://github.com/leeseangm-dot/ziwei-quanshu.git ~/.workbuddy/skills/ziwei-quanshu
```

> **Sharing across tools**: if you already installed to `~/.agents/skills/`, symlink it so tools
> that only scan their own directory can still find it — no need to maintain multiple copies:
> ```bash
> ln -s ~/.agents/skills/ziwei-quanshu ~/.workbuddy/skills/ziwei-quanshu   # macOS / Linux
> # Windows (administrator PowerShell):
> # New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.workbuddy\skills\ziwei-quanshu" `
> #   -Target "$env:USERPROFILE\.agents\skills\ziwei-quanshu"
> ```

### Option 3: clients that don't understand skills

If your tool doesn't support skill directories (pure chat products such as Doubao), **the script
still works standalone** — charting depends on no AI at all:

```bash
git clone https://github.com/leeseangm-dot/ziwei-quanshu.git
cd ziwei-quanshu
# produces an HTML chart file directly
python3 scripts/ziwei_pan.py --solar 1990-05-15 --shichen 午 --sex 男
# if the tool can only read text, use md output and paste it in
python3 scripts/ziwei_pan.py --solar 1990-05-15 --shichen 午 --sex 男 --format md
```

Charting works anywhere `python3` is available, independent of any AI; open the generated HTML
chart in a browser. The knowledge base (`chapters/`, `patterns.md`, `cheatsheet.md`) is plain
markdown and can be fed to such a tool as reference material.

## Usage

In a skill-capable client (WorkBuddy / Claude Code / Codex / Cursor, etc.), any of these keywords
triggers the skill:

`紫微斗数` `紫微` `斗数` `紫微命盘` `排紫微盘` `看紫微` `命宫` `身宫` `十二宫` `四化` `庙旺落陷` `大限流年` `ziwei`

The skill then walks you through supplying birth data, calls the charting script, and produces a
full analysis. Once the data is confirmed it runs (HTML output by default):

```bash
python3 scripts/ziwei_pan.py --solar 1990-05-15 --shichen 午 --sex 男
```

Equivalent invocations:

```bash
python3 scripts/ziwei_pan.py --solar 1990-05-15 --hour 12:00 --sex 男   # by clock time
python3 scripts/ziwei_pan.py --lunar 1990-04-21 --shichen 午 --sex 男   # by lunar date
python3 scripts/ziwei_pan.py --lunar 2020-04-01 --leap --hour 12:00 --sex 女  # leap lunar month
python3 scripts/ziwei_pan.py --solar 1990-05-15 --shichen 午 --sex 男 --format md  # text only
```

### Main arguments

| Argument | Meaning |
|---|---|
| `--solar YYYY-MM-DD` | Solar (Gregorian) birth date |
| `--lunar YYYY-MM-DD` | Lunar birth date (year-month-day as digits) |
| `--leap` | Lunar leap month |
| `--hour HH:MM` / `--shichen 子..亥` | Birth time (mutually exclusive; omit both for unknown hour) |
| `--longitude 104.07` | **Birthplace longitude (°E)**: converts `--hour` from clock time to true solar time before fixing the shichen |
| `--no-true-solar` | Disable the true-solar-time correction; use clock time directly |
| `--sex 男\|女` | **Required** |
| `--year YYYY` | Year to forecast (defaults to the current year) |
| `--daxian quanshu\|common` | Major-limit starting palace (default `quanshu`, per the source book) |
| `--leap-policy next-month\|split15` | Leap-month convention (default `next-month`, per the source book) |
| `--year-divide exact\|day` | Year-pillar boundary (default `exact`, the precise instant of 立春) |
| `--late-zishi next-day\|same-day` | Late zi-hour attribution (default `next-day`) |
| `--format html\|md\|both` | Output format (**default `html`**; `md` goes to stdout) |
| `--out <path>` | HTML output path (defaults to an auto-generated name) |
| `--interpret <file.md>` | Inject interpretation markdown into the HTML slots |
| `--stdout-html` | Write HTML to stdout instead of a file |
| `--title "…"` | HTML page title (auto-generated by default) |

**Output modes**: `html` (default, writes a file) / `md` (text to stdout) / `both`.
Progress and warnings go to stderr, so HTML never mixes into stdout and redirection is safe.

### Three schools of practice

Three rules differ between commentators. The script **defaults to the source book's conventions**
and provides switches to align with external software:

| Point of divergence | Source-book convention (default) | Common practice | Switch |
|---|---|---|---|
| Major-limit start | Yang-male / Yin-female start at the **Parents palace** going forward; Yin-male / Yang-female start at the **Siblings palace** going backward | most software starts at the **Life palace** | `--daxian` |
| Leap-month placement | a leap month counts as the **following month** | split the leap month in half (first half = this month, second half = next) | `--leap-policy` |
| Year-pillar boundary | the **precise instant** of 立春 | switches on the **day** of 立春 | `--year-divide` |

> To compare charts against external software (iztro and similar) you must switch all three,
> otherwise the whole chart shifts:
> ```bash
> python3 scripts/ziwei_pan.py --solar 1990-05-15 --hour 12:00 --sex 男 \
>     --daxian common --leap-policy split15 --year-divide day
> ```

> **Note**: those three are *convention* differences and unrelated to true solar time.
> True solar time is a **more fundamental layer** — it decides whether the shichen itself is
> right. If the hour is wrong, no combination of the three switches yields a correct chart.

## Sources

| Text | Use |
|------|------|
| 《紫微斗数全书》太微赋·形性赋 | star natures and general principles |
| 《紫微斗数全书》斗数准绳·发微论 | star enclosures; essentials of fixing the Life palace |
| 《紫微斗数全书》诸星问答论 | the fourteen major stars and the supporting/malefic stars |
| 《紫微斗数全书》骨髓赋（男/女） | patterns and overall rank of a fate |
| 《紫微斗数全书》安星诀 | placing Life/Body, raising Zi Wei, placing the stars |
| 《紫微斗数全书》十二宫论断 | the twelve palaces' respective duties |
| 《斗数宣微》 | secondary reference on star interactions |
| 《十八飞星策天紫微斗数》 | secondary reference on the older flying-star method |

## Project structure

```
ziwei-quanshu/
├── SKILL.md                        # Skill entry (three-stage workflow + core framework)
├── scripts/
│   ├── ziwei_pan.py                #   charting script (stdlib only, no pip; HTML by default)
│   ├── ziwei_html.py               #   HTML chart renderer (zero dependencies)
│   ├── test_ziwei_pan.py           #   charting regression tests + external-library cross-check
│   └── test_ziwei_html.py          #   HTML rendering regression tests
├── references/
│   └── paipan-rules.md             #   charting rules quick reference (same conventions as the script)
├── chapters/                       #   16 chapters distilled from the source text
│   ├── ch01-xu-yu-zonggang.md      #     Luo's preface and Tai Wei Fu
│   ├── ch02-xingxing-fu.md         #     Xing Xing Fu (star natures)
│   ├── ch03-zhunsheng-fawei.md     #     Xing Yuan Lun / Dou Shu Zhun Sheng / Fa Wei Lun
│   ├── ch04-zhuxing-wenda.md       #     Zhu Xing Wen Da Lun (part 1)
│   ├── ch05-fuxing-sihua-shaxing.md#     Zhu Xing Wen Da Lun (part 2)
│   ├── ch06-gusui-fu.md            #     Gu Sui Fu
│   ├── ch07-nvming-gusui.md        #     Gu Sui Fu for female fates
│   ├── ch08-geju-lun.md            #     Ge Ju Lun (patterns)
│   ├── ch09-anshen-mingli.md       #     An Shen Ming examples and general rules
│   ├── ch10-anxing-jue.md          #     An Xing Jue (star-placement verses)
│   ├── ch11-miaowang-wuxing.md     #     temple states and north/south dipper five-element assignments
│   ├── ch12-shiergong-shang.md     #     On the twelve palaces (part 1)
│   ├── ch13-shiergong-xia.md       #     On the twelve palaces (part 2)
│   ├── ch14-tanxing-yaolun.md      #     Tan Xing Yao Lun and rank of a fate
│   ├── ch15-daxian-liunian.md      #     major limits, minor limits and annual fortune
│   └── ch16-zhuxing-tongyuan.md    #     star combinations and their respective suitability
├── glossary.md                     # glossary of terms
├── patterns.md                     # interpretation patterns
├── cheatsheet.md                   # decision-rule quick reference
├── LICENSE
├── README.md                       # documentation (Chinese)
└── README.en.md                    # documentation (English)
```

## Verification

```bash
python3 scripts/test_ziwei_pan.py            # classic verse anchors (137 assertions)
python3 scripts/test_ziwei_pan.py --cross    # plus cross-check against an external library
python3 scripts/test_ziwei_html.py           # HTML rendering regression (189 assertions)
```

`test_ziwei_html.py` covers: 4×4 grid placement, all twelve palaces present, major/supporting/minor
star tiers, temple states and Four Transformation markers, interpretation-slot parsing and
injection, markdown→HTML escaping, render determinism, absence of external resources (works
offline), Chinese lunar month/day wording, and **md text ↔ HTML chart consistency**.

The charting algorithm implements the source text's star-placement verses line by line, and was
compared against an independent external library (iztro) over 1200+ random charts:
**Life palace, Body palace, Five-Element Bureau, Zi Wei / Tian Fu and the fourteen major stars all
match one-to-one.** Lunar conversion was separately checked against an authoritative calendar
library (lunar-javascript) across 1500 days.

HTML rendering was additionally compared palace by palace against a hand-written reference chart:
**all twelve palaces' stars are covered** (the long-life / twelve-officer / minor stars the
reference chart omitted are supplied by the script and were each verified individually).

A few error-prone points are explicitly calibrated; see `references/paipan-rules.md`:

- the **day granularity** of leap-month determination (most error-prone when a new moon and a
  solar term fall on the same day)
- the **instant granularity** of the year-pillar boundary (before and after the moment of 立春
  belong to different years)
- the Zi Wei placement rule "quotient steps forward from the palace, remainder retreats on odd /
  advances on even"
- the north/south dipper timing rule pairs by **Yang-male/Yin-female vs. Yin-male/Yang-female**
  (same polarity → south dipper, opposite → north dipper), not by sex alone

## Disclaimer

This skill is for the study of traditional culture and for entertainment. Its output does not
constitute a basis for any decision. Astrology belongs to the domain of traditional culture;
please treat it rationally. The source text's verdicts carry Ming-dynasty assumptions (for example,
derogatory language about women and disparagement of "monks and Daoists"); this skill preserves
them as-is for study purposes and **does not endorse them as contemporary values**.
