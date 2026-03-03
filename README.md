# 📚 Finance Journal Bot — 自动化财经论文订阅机器人

> **一句话描述：** 这是一个运行在 GitHub Actions 免费云服务器上的定时机器人，它每半个月自动抓取国际顶级财经期刊的最新论文，通过关键词过滤 + AI 智能筛选后，以精美的 HTML 邮件形式发送到你的邮箱。

---

## 目录

- [📖 项目概述](#-项目概述)
- [🗂️ 文件结构](#️-文件结构)
- [⚙️ 核心文件详解](#️-核心文件详解)
  - [requirements.txt](#requirementstxt)
  - [main.py](#mainpy)
  - [.github/workflows/main.yml](#githubworkflowsmainyml)
  - [finance\_journals.db](#finance_journalsdb)
- [🔄 完整工作流程](#-完整工作流程)
  - [第一次手动操作（初始化）](#第一次手动操作初始化)
  - [后续定期自动执行](#后续定期自动执行)
- [⏰ YAML 的持续作用（重点！）](#-yaml-的持续作用重点)
- [🖥️ 虚拟机的临时特性](#️-虚拟机的临时特性)
- [🧠 main.py 业务逻辑详解](#-mainpy-业务逻辑详解)
- [🔧 YAML 配置深度解析](#-yaml-配置深度解析)
- [🚀 快速开始指南](#-快速开始指南)
- [🛠️ 故障排除与常见问题](#️-故障排除与常见问题)

---

## 📖 项目概述

### 这是什么？

`finance_journal_bot` 是一个**完全自动化的学术论文推送系统**，专为财经研究人员设计。它的核心能力是：

| 功能 | 说明 |
|------|------|
| 🕷️ **多源抓取** | 同时监控 12 本中英文顶级期刊的 RSS 订阅源 |
| 🔍 **智能过滤** | 两层过滤：关键词白名单 + DeepSeek AI 判断 |
| 📧 **邮件推送** | 自动生成带摘要、WebVPN 链接的精美 HTML 邮件 |
| 💾 **去重存储** | SQLite 数据库记录已推送论文，避免重复 |
| ☁️ **云端运行** | 完全运行在 GitHub Actions 免费虚拟机上，无需本地服务器 |
| 🔄 **自动同步** | 每次运行后将数据库更新推回 GitHub 仓库永久保存 |

### 监控的期刊列表

**英文顶级期刊：**
- Journal of Finance (JF)
- Journal of Financial Economics (JFE)
- Review of Financial Studies (RFS)
- Journal of Financial and Quantitative Analysis (JFQA)
- Management Science
- Review of Finance

**中文顶级期刊：**
- 经济研究
- 管理世界
- 金融研究
- 数量经济技术经济研究
- 中国工业经济
- 经济学季刊

---

## 🗂️ 文件结构

```
finance_journal_bot/
│
├── .github/
│   └── workflows/
│       └── main.yml          # ⚙️ GitHub Actions 自动化配置（大脑）
│
├── main.py                   # 🐍 核心业务逻辑（心脏）
├── requirements.txt          # 📦 Python 依赖列表
├── finance_journals.db       # 💾 SQLite 数据库（记忆）
└── README.md                 # 📖 本文档
```

**文件关系图：**

```
main.yml (调度器)
    │
    ├──► 触发 GitHub Actions 虚拟机
    │         │
    │         ├── 安装 requirements.txt 中的依赖
    │         │
    │         ├── 运行 main.py
    │         │       ├── 读取 finance_journals.db（查重）
    │         │       ├── 抓取 RSS → 关键词过滤 → AI 过滤
    │         │       ├── 发送邮件
    │         │       └── 写入 finance_journals.db（记录）
    │         │
    │         └── 将更新后的 finance_journals.db 推回 GitHub
```

---

## ⚙️ 核心文件详解

### `requirements.txt`

```
feedparser
beautifulsoup4
openai
```

| 依赖包 | 用途 |
|--------|------|
| `feedparser` | 解析 RSS/Atom 订阅源，提取论文标题、链接、摘要、发布日期等结构化信息 |
| `beautifulsoup4` | 清洗 HTML 标签，将 RSS 中带有 HTML 标记的摘要转换为纯文本，便于 AI 阅读 |
| `openai` | 调用 OpenAI 兼容接口（这里实际对接的是 DeepSeek），发送 AI 判断请求 |

> **注意：** Python 标准库中的 `smtplib`、`sqlite3`、`ssl`、`os` 等模块**无需安装**，已内置在 Python 中。

---

### `main.py`

这是整个机器人的"心脏"，包含所有核心业务逻辑。

#### 配置区域（第 14-68 行）

```python
# ===== 环境变量（从 GitHub Secrets 读取）=====
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL")     # 发件人邮箱
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")  # 邮箱授权码（非登录密码）
RECEIVER_EMAIL  = os.environ.get("RECEIVER_EMAIL")   # 收件人邮箱
LLM_API_KEY     = os.environ.get("LLM_API_KEY")      # AI API 密钥

# ===== 第一层过滤：关键词白名单 =====
MUST_HAVE_KEYWORDS = [
    "fintech", "financial technology",
    "machine learning", "deep learning", "neural network",
    "climate risk", "esg", "textual analysis",
    "金融科技", "机器学习", "深度学习", "神经网络", "文本分析",
    "大语言模型", "高频交易", "量化投资"
]

# ===== 第二层过滤：AI 判断标准 =====
USER_INTEREST_DESCRIPTION = """
我的研究兴趣非常广泛，请采取【宽容策略】，只要文章符合以下任意一个方向，都回答 Yes：
1. 金融科技 (FinTech)：涉及高频交易、市场微观结构、支付、区块链、数字货币...
2. AI与大数据：金融中的机器学习、NLP文本分析、情感分析、高维数据预测
3. 资产定价：股票收益预测、因子模型、量化策略
4. 计量：因果推断模型、计量模型
"""

# ===== RSS 订阅源 =====
RSS_FEEDS = {
    "Journal of Finance": "https://onlinelibrary.wiley.com/feed/15406261/most-recent",
    "JFE":  "https://www.sciencedirect.com/science/journal/0304405X/rss",
    # ... 共 12 本期刊
}
```

#### 核心函数说明

| 函数 | 功能 |
|------|------|
| `init_db()` | 初始化 SQLite 数据库，创建 `articles` 表（如果不存在） |
| `is_new(link)` | 查询数据库，判断某篇论文是否已处理过（通过 URL 去重） |
| `save_article(...)` | 将已处理的论文信息写入数据库 |
| `clean_html(raw)` | 用 BeautifulSoup 剥离 HTML 标签，返回纯文本摘要 |
| `get_ai_judgement(title, abstract)` | 调用 DeepSeek AI，判断论文是否符合用户兴趣，返回 `True`/`False` |
| `get_zju_vpn_link(url)` | 将普通论文链接转换为浙江大学 WebVPN 格式，方便校园网访问 |
| `send_email(subject, html)` | 通过 QQ 邮箱 SMTP SSL 协议发送 HTML 格式邮件 |
| `run_job()` | **主流程**：遍历所有期刊 → 过滤 → 生成邮件 → 发送 → 存库 |

#### `run_job()` 主流程详解

```
开始
 │
 ├── 遍历 RSS_FEEDS 中的每本期刊
 │       │
 │       ├── 用 feedparser 解析 RSS（每本取最新 20 篇）
 │       │
 │       └── 对每篇论文：
 │               │
 │               ├── [查重] is_new(link)?
 │               │     ├── 否 → 跳过
 │               │     └── 是 → 继续
 │               │
 │               ├── [第一层] 标题含关键词? → 标记为感兴趣
 │               │
 │               ├── [第二层] 未命中关键词 → 调用 AI 判断
 │               │
 │               └── 记录论文信息（含是否感兴趣标志）
 │
 ├── 有新论文? 
 │     ├── 否 → 打印日志，结束
 │     └── 是 → 生成 HTML 邮件
 │               │
 │               ├── 感兴趣的论文：橙色加粗 + 显示摘要 + 💡 图标
 │               └── 普通论文：蓝色 + 无摘要
 │
 ├── 发送邮件
 │
 └── 成功后 → 将所有新论文写入 SQLite 数据库
```

---

### `.github/workflows/main.yml`

这是 GitHub Actions 的"调度配置文件"，告诉 GitHub **何时运行**、**如何运行**这个机器人。

```yaml
name: Monthly Finance Bot    # 工作流的名称（显示在 GitHub Actions 页面）

on:                          # 触发条件
  schedule:
    - cron: '0 9 1,15 * *'  # 定时触发：UTC 09:00 = 北京时间 17:00，每月1日和15日
  workflow_dispatch:         # 允许在 GitHub 网页上手动点击触发

permissions:
  contents: write            # 授权写权限（用于将更新的数据库 push 回仓库）

jobs:
  run_bot:                   # 任务名称
    runs-on: ubuntu-latest   # 在 Ubuntu 最新版虚拟机上运行

    steps:
      - uses: actions/checkout@v3        # 第1步：把仓库代码下载到虚拟机
      - uses: actions/setup-python@v4    # 第2步：安装 Python 3.9
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt  # 第3步：安装依赖
      - env:                             # 第4步：注入环境变量（Secrets）并运行机器人
          SENDER_EMAIL: ${{ secrets.SENDER_EMAIL }}
          SENDER_PASSWORD: ${{ secrets.SENDER_PASSWORD }}
          RECEIVER_EMAIL: ${{ secrets.RECEIVER_EMAIL }}
        run: python main.py
      - run: |                           # 第5步：将更新的数据库推回 GitHub
          git config --global user.name "GitHub Action Bot"
          git config --global user.email "actions@github.com"
          git add finance_journals.db
          git commit -m "Update database records [skip ci]" || exit 0
          git pull --rebase origin main
          git push
```

---

### `finance_journals.db`

这是 SQLite 数据库文件，作为机器人的"长期记忆"，存储所有已处理过的论文记录。

**数据库结构：**

```sql
CREATE TABLE articles (
    link           TEXT PRIMARY KEY,  -- 论文 URL（唯一标识，用于去重）
    title          TEXT,              -- 论文标题
    journal        TEXT,              -- 所属期刊名称
    published_date TEXT               -- 发布日期（格式：YYYY-MM-DD）
);
```

**为什么要存储到数据库并推回 GitHub？**

> 因为 GitHub Actions 虚拟机在每次执行完毕后会被销毁，所有数据都会丢失。将数据库文件保存在 GitHub 仓库中，是唯一让机器人拥有"记忆"的方式——下次虚拟机启动时，第一步就会 `checkout` 下载包含历史记录的数据库。

---

## 🔄 完整工作流程

### 第一次手动操作（初始化）

```
你的电脑                   GitHub 仓库                  GitHub Actions
   │                          │                               │
   ├── git push ──────────────►│                               │
   │   (上传所有文件)           │                               │
   │                          │◄── GitHub 检测到新 YAML ───────┤
   │                          │    并注册定时任务               │
   │                          │                               │
   └────────────────────────────────────────────────────────►│
                                                              │ ← 从此开始，
                                                              │   YAML 永久
                                                              │   保存在云端
```

**第一次 `git push` 做了什么？**

1. 将 `main.py`、`requirements.txt`、`finance_journals.db`、`.github/workflows/main.yml` 上传到 GitHub
2. GitHub 检测到 `.github/workflows/` 目录下的 YAML 文件，**自动注册定时任务**
3. 从此，GitHub 的调度系统会按照 YAML 中的 cron 表达式，**永久定期触发**这个工作流

> ⚠️ **为什么必须手动 push 一次？**
> GitHub 只有在你把 YAML 文件 push 到仓库后，才能"读到"你的定时计划。没有这一步，GitHub 根本不知道要为你做什么。这就像你需要先"报名"才能让系统帮你"定时提醒"。

---

### 后续定期自动执行

每月1日和15日北京时间17:00，以下流程**全自动**发生：

```
GitHub 定时器                虚拟机（临时）                   你的邮箱
    │                            │                              │
    ├── 触发工作流 ──────────────►│（新虚拟机启动）               │
    │                            │                              │
    │                            ├── Checkout 代码              │
    │                            │   (含历史数据库)              │
    │                            │                              │
    │                            ├── 安装 Python 依赖           │
    │                            │                              │
    │                            ├── 运行 main.py               │
    │                            │   ├── 读数据库（查重）        │
    │                            │   ├── 抓取 12 本期刊 RSS     │
    │                            │   ├── 关键词过滤              │
    │                            │   ├── AI 判断                │
    │                            │   ├── 生成 HTML 邮件          │
    │                            │   └── 发送邮件 ──────────────►│
    │                            │                              │
    │                            ├── 更新数据库                  │
    │                            └── git push 数据库 ──────────►GitHub 仓库
    │                            │（虚拟机销毁）                 │
```

---

## ⏰ YAML 的持续作用（重点！）

> 这是最容易被误解的部分，请仔细阅读。

很多人以为 YAML 文件"只在第一次 push 时有用"，这是**错误的**。

### ✅ YAML 的真实工作机制

| 常见误解 ❌ | 正确理解 ✅ |
|------------|------------|
| YAML 只用一次，push 后就不管它了 | YAML **永久保存**在 GitHub 仓库云端 |
| 定时任务一旦注册就固定不变 | GitHub **每次触发前都重新读取** YAML |
| 改了 YAML 需要重新注册 | **不需要！** 只需 push，下次自动按新配置运行 |
| 删除 YAML 不影响已有定时任务 | 删除 YAML → 定时任务**立即停止** |

### YAML 是"你和 GitHub 的对话语言"

```
你写的 YAML                     GitHub 理解的意思
─────────────────────────────────────────────────────
cron: '0 9 1,15 * *'    →    "好的，我每月1日和15日UTC09:00叫你"
runs-on: ubuntu-latest   →    "好的，我给你准备一台Ubuntu虚拟机"
secrets.SENDER_EMAIL     →    "好的，我把你保存的密钥注入环境变量"
contents: write          →    "好的，我允许这个工作流写入你的仓库"
```

**每次触发时，GitHub 都会：**

```
1. 读取仓库中最新的 .github/workflows/main.yml
2. 按照 YAML 的配置启动虚拟机
3. 按照 YAML 的 steps 顺序执行每一步
4. 使用 YAML 中引用的 secrets
5. 执行完毕，销毁虚拟机
```

> 💡 **类比：** YAML 就像是你在外卖 App 上设置的"每月1日自动下单"规则。这个规则保存在 App 的服务器上，即使你关了手机，到时间它仍会自动执行。修改规则不需要"重新注册"，只需要在 App 里更新保存即可。

---

## 🖥️ 虚拟机的临时特性

GitHub Actions 的执行环境是**完全临时**的：

```
第1次运行（1月1日）：
  [启动] 全新的 Ubuntu 虚拟机
    → 下载仓库代码（含数据库 v1）
    → 运行机器人，发邮件
    → 更新数据库 → git push（数据库 v2 上传到 GitHub）
  [销毁] 虚拟机消失，什么都不剩

第2次运行（1月15日）：
  [启动] 又一台全新的 Ubuntu 虚拟机（和上次完全无关）
    → 下载仓库代码（含数据库 v2，因为上次 push 了）
    → 运行机器人，用数据库 v2 去重，发邮件
    → 更新数据库 → git push（数据库 v3 上传到 GitHub）
  [销毁] 虚拟机消失
```

**关键点：**

- 🆕 每次运行都是**全新环境**：Python 重新安装，依赖重新安装，没有任何"上次的状态"
- 🔗 唯一的"记忆"通过 GitHub 仓库传递：`finance_journals.db` 上传到 GitHub → 下次被 checkout 下载
- 💰 完全**免费**：GitHub Actions 对公开仓库免费，每月约 2000 分钟

---

## 🧠 main.py 业务逻辑详解

### 论文过滤的两层策略

```
每篇新论文
    │
    ▼
[第一层：关键词白名单] ───── 快、免费
    │
    ├── 标题包含 MUST_HAVE_KEYWORDS 中任意一个关键词？
    │     ├── ✅ 是 → 标记为"感兴趣"，跳过 AI
    │     └── ❌ 否 → 进入第二层
    │
    ▼
[第二层：AI 判断] ─────────── 慢、消耗 API
    │
    ├── 将标题 + 摘要发送给 DeepSeek
    ├── Prompt 采用"宽容策略"（宁可错判也不漏掉）
    └── 回答 "Yes" → 标记为"感兴趣"
        回答 "No"  → 普通论文（仍会在邮件中显示）
```

**为什么两层过滤？**

关键词匹配速度极快，能处理大多数明显相关的论文，节省 AI API 调用费用。AI 判断则能理解语义，捕捉关键词未覆盖的相关论文。

### 邮件样式说明

| 论文类型 | 标题样式 | 额外显示 | 图标 |
|----------|----------|----------|------|
| 感兴趣（AI/关键词命中） | 橙色加粗大字 | 摘要前 300 字 | 💡 |
| 普通论文 | 蓝色加粗 | 无摘要 | — |

每篇论文都提供两个访问链接：
- 🏫 **浙大 WebVPN 直连**：自动将论文 URL 转换为 `xxx.webvpn.zju.edu.cn` 格式
- 🔍 **Google Scholar**：按标题搜索，方便找到论文信息

---

## 🔧 YAML 配置深度解析

### `on:` 字段 — 触发条件

```yaml
on:
  schedule:
    - cron: '0 9 1,15 * *'
  workflow_dispatch:
```

**Cron 表达式解读：**

```
  0    9    1,15    *    *
  │    │      │     │    │
  │    │      │     │    └── 星期几（* = 任意）
  │    │      │     └─────── 月份（* = 任意）
  │    │      └───────────── 日期（1日和15日）
  │    └──────────────────── 小时（UTC 09:00）
  └───────────────────────── 分钟（0分）

结论：每月1日和15日的 UTC 09:00 = 北京时间 17:00
```

**`workflow_dispatch:`** 的作用：在 GitHub 仓库的 Actions 页面显示一个"Run workflow"按钮，允许随时手动触发，方便测试。

### `permissions:` 字段

```yaml
permissions:
  contents: write
```

默认情况下，GitHub Actions 只有**读取**仓库内容的权限。添加 `contents: write` 后，工作流才能执行 `git push`，将更新的数据库文件推回仓库。

### `steps:` 执行顺序

| 步骤 | 名称 | 实际执行 | 耗时约 |
|------|------|----------|--------|
| 1 | Checkout code | 将仓库内容（含数据库）下载到虚拟机 | ~10s |
| 2 | Set up Python | 安装 Python 3.9 运行环境 | ~10s |
| 3 | Install dependencies | `pip install feedparser beautifulsoup4 openai` | ~20s |
| 4 | Run Bot Script | 执行 `python main.py`（主要耗时在此） | 1-5min |
| 5 | Commit and Push DB changes | 更新数据库并推回 GitHub | ~15s |

---

## 🚀 快速开始指南

### 前置条件

- GitHub 账号
- QQ 邮箱（用于发送邮件）
- DeepSeek API 密钥（[申请地址](https://platform.deepseek.com/)）

### 步骤一：Fork 本仓库

点击 GitHub 页面右上角的 **Fork** 按钮，将本仓库 fork 到你自己的账号下。

### 步骤二：配置 GitHub Secrets

进入你 fork 后的仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

添加以下 4 个 Secret：

| Secret 名称 | 填写内容 | 如何获取 |
|-------------|----------|----------|
| `SENDER_EMAIL` | 发件人 QQ 邮箱地址 | 你的 QQ 邮箱 |
| `SENDER_PASSWORD` | QQ 邮箱授权码（非登录密码！） | QQ邮箱 → 设置 → 账户 → 开启SMTP服务 |
| `RECEIVER_EMAIL` | 收件人邮箱地址 | 你想接收推送的邮箱 |
| `LLM_API_KEY` | DeepSeek API 密钥 | [platform.deepseek.com](https://platform.deepseek.com/) |

> ⚠️ **SENDER_PASSWORD 是授权码，不是 QQ 密码！**
> 在 QQ 邮箱网页版 → 设置 → 账户 → 找到"开启IMAP/SMTP服务"，点击开启后会生成一个16位授权码，填写这个码。

### 步骤三：自定义配置（可选）

在 `main.py` 中修改：

```python
# 调整关键词（与你的研究方向相关）
MUST_HAVE_KEYWORDS = [
    "your keyword 1",
    "your keyword 2",
    # ...
]

# 调整 AI 判断标准
USER_INTEREST_DESCRIPTION = """
你的研究兴趣描述...
"""
```

### 步骤四：触发第一次运行

1. 将修改后的代码 `git push` 到你的 GitHub 仓库
2. 进入仓库 → **Actions** → **Monthly Finance Bot**
3. 点击 **Run workflow** → **Run workflow**（手动触发测试）
4. 等待约 2-5 分钟，检查你的邮箱

### 步骤五：验证运行

在 GitHub Actions 页面，点击最新的运行记录，查看每个步骤的日志：

```
✅ Checkout code
✅ Set up Python
✅ Install dependencies
✅ Run Bot Script       ← 在这里查看抓取日志
✅ Commit and Push DB changes
```

---

## 🛠️ 故障排除与常见问题

### ❓ 邮件没有收到

**检查步骤：**
1. 进入 GitHub Actions，查看 "Run Bot Script" 步骤的日志
2. 搜索日志中的 `Email Error:` 关键词

**常见原因：**

| 错误信息 | 原因 | 解决方法 |
|----------|------|----------|
| `SMTPAuthenticationError` | 授权码错误 | 重新生成 QQ 邮箱授权码，更新 Secret |
| `Connection refused` | SMTP 配置问题 | 确认 QQ 邮箱已开启 IMAP/SMTP 服务 |
| `No new articles` | 当前没有新论文 | 正常现象，等下次运行 |
| `SENDER_PASSWORD` 为空 | Secret 未配置 | 检查 GitHub Secrets 是否正确填写 |

### ❓ AI 判断不工作（所有论文只靠关键词）

**检查：** 查看日志中 `LLM_API_KEY` 是否为空

```python
# main.py 中的保护逻辑
def get_ai_judgement(title, abstract):
    if not LLM_API_KEY: return False   # ← API Key 为空时直接跳过
```

**解决：** 在 GitHub Secrets 中添加 `LLM_API_KEY`

### ❓ 定时任务不执行

**可能原因：**
1. **GitHub 对低活跃仓库的限制：** 如果仓库 60 天内没有任何活动，GitHub 会暂停定时工作流。解决方法：偶尔手动运行一次，或在代码中添加 `keep-alive` 机制。
2. **YAML 语法错误：** 在 [YAML Lint](https://www.yamllint.com/) 检验你的 YAML 文件。
3. **Cron 时区问题：** GitHub Actions 的 cron 使用 UTC 时区，请注意换算。

### ❓ 数据库推送失败

**日志报错：** `remote: Permission denied`

**解决：** 确认工作流的 `permissions` 设置包含 `contents: write`：
```yaml
permissions:
  contents: write
```

### 🔍 如何查看详细日志

1. 打开 GitHub 仓库
2. 点击 **Actions** 标签
3. 点击最近一次运行记录
4. 展开每个步骤查看详细输出

```
Actions 页面截图位置：
https://github.com/你的用户名/finance_journal_bot/actions
```

### 💡 调试技巧

**临时添加打印语句：** 在 `main.py` 中添加 `print()` 调试信息，这些信息会出现在 Actions 日志中。

**手动触发而非等定时：** 每次调试时使用 `workflow_dispatch` 手动触发，不必等到1日/15日。

**检查 RSS 源是否有效：** 在浏览器中直接访问 `RSS_FEEDS` 中的 URL，看是否能返回 XML 数据。

---

## 📊 项目数据流总结

```
RSS 源 (12本期刊)
    │
    ▼
feedparser 解析
    │
    ▼
is_new() 去重查询 ─── finance_journals.db
    │
    ├── 关键词匹配 (快速)
    │
    └── AI 判断 (精准) ─── DeepSeek API
            │
            ▼
        HTML 邮件生成
            │
            ▼
        smtplib 发送 ─── 你的邮箱 📧
            │
            ▼
        save_article() ─── finance_journals.db (更新)
            │
            ▼
        git push ─── GitHub 仓库 (持久化)
```

---

## 📄 许可证

MIT License — 自由使用、修改和分发。

---

*最后更新：2026-03*