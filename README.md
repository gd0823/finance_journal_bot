# 📊 Finance Journal Bot — 自动化财经论文订阅机器人

> 自动抓取顶级财经期刊的最新论文，通过 AI 筛选感兴趣的内容，定期发送邮件摘要，并将已处理记录存入数据库实现去重。

---

## 目录

1. [项目概述](#1-项目概述)
2. [完整工作流程图](#2-完整工作流程图)
3. [项目文件结构与功能](#3-项目文件结构与功能)
4. [YAML 配置详解](#4-yaml-配置详解)
5. [main.py 业务流程详解](#5-mainpy-业务流程详解)
6. [工作流生命周期](#6-工作流生命周期)
7. [快速开始指南](#7-快速开始指南)
8. [故障排除](#8-故障排除)

---

## 1. 项目概述

本项目是一个运行在 **GitHub Actions** 上的自动化机器人，无需任何本地服务器即可持续运行。它的核心功能如下：

| 功能 | 说明 |
|------|------|
| 📡 RSS 抓取 | 订阅 12 个中英文顶级财经期刊的 RSS 源 |
| 🔍 关键词过滤 | 通过预设关键词快速初筛（FinTech、机器学习等） |
| 🤖 AI 智能判断 | 调用 DeepSeek 大模型对未命中关键词的论文进行二次判别 |
| 📧 邮件推送 | 将筛选结果以精美 HTML 格式发送到指定邮箱 |
| 💾 数据库去重 | 使用 SQLite 记录已处理文章，避免重复推送 |
| ⏰ 定时执行 | 每月 1 日和 15 日自动触发，也支持手动触发 |

**订阅的期刊列表：**

| 类别 | 期刊名称 |
|------|---------|
| 英文顶刊 | Journal of Finance、JFE、RFS、JFQA、Management Science、Review of Finance |
| 中文顶刊 | 经济研究、管理世界、金融研究、数量经济技术经济研究、中国工业经济、经济学季刊 |

---

## 2. 完整工作流程图

### 2.1 整体生命周期（首次 → 后续自动运行）

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GitHub 仓库                                  │
│                                                                      │
│  ① 首次操作                   ② 每月 1日/15日 自动触发               │
│  手动 Push 代码                (或随时手动点击 Run workflow)          │
│       │                                    │                         │
│       ▼                                    ▼                         │
│  ┌─────────────┐              ┌────────────────────────┐             │
│  │  GitHub     │              │   GitHub Actions        │             │
│  │  Actions    │◄─────────────│   定时调度器 (cron)     │             │
│  │  触发工作流  │              └────────────────────────┘             │
│  └──────┬──────┘                                                     │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────────────────────────────────────────┐               │
│  │          全新 Ubuntu 虚拟机（每次全新启动）          │               │
│  │                                                  │               │
│  │  Step 1: Checkout → 拉取仓库代码（含 .db 文件）    │               │
│  │  Step 2: Setup Python 3.9                        │               │
│  │  Step 3: pip install -r requirements.txt         │               │
│  │  Step 4: python main.py                          │               │
│  │  Step 5: git push → 推送更新的 .db 回仓库         │               │
│  │                                                  │               │
│  └──────────────────────────────────────────────────┘               │
│         │                                                            │
│         ▼                                                            │
│  虚拟机销毁（临时环境，每次重建）                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 `python main.py` 内部执行流程

```
main.py 启动
    │
    ▼
init_db() — 初始化数据库（首次创建表，后续直接使用已有数据）
    │
    ▼
run_job() — 主循环
    │
    ├─── 对每个 RSS 源（共 12 个期刊）
    │         │
    │         ▼
    │    feedparser.parse(url) — 抓取最新文章（最多取前 20 篇）
    │         │
    │         ▼
    │    对每篇文章：
    │         │
    │         ├─► is_new(link)? ─── No ──► 跳过（已处理过）
    │         │       │
    │         │      Yes
    │         │       │
    │         │       ▼
    │         │  关键词检查（MUST_HAVE_KEYWORDS）
    │         │       │
    │         │    命中 ──────────────────────────────────────────► is_match = True
    │         │       │
    │         │    未命中
    │         │       │
    │         │       ▼
    │         │  AI 判断（get_ai_judgement → DeepSeek API）
    │         │       │
    │         │  Yes ─┤
    │         │       │──────────────────────────────────────────► is_match = True
    │         │  No ──┤
    │         │       │──────────────────────────────────────────► is_match = False
    │         │       │
    │         │       ▼
    │         │  加入 monthly_data（感兴趣的排前面）
    │         │  加入 pending_save 列表
    │
    ▼
有新文章？
    │
   Yes
    │
    ▼
生成 HTML 邮件正文
    │
    ▼
send_email() — 通过 QQ 邮箱 SMTP 发送
    │
   成功
    │
    ▼
将 pending_save 中所有文章写入数据库（save_article）
    │
    ▼
git add / commit / pull --rebase / push → 数据库同步回 GitHub
    │
   No（无新文章）
    │
    ▼
打印 "No new articles." 并退出
```

---

## 3. 项目文件结构与功能

```
finance_journal_bot/
├── .github/
│   └── workflows/
│       └── main.yml          # GitHub Actions 工作流配置（自动化引擎）
├── main.py                   # 核心业务逻辑脚本
├── requirements.txt          # Python 依赖列表
├── finance_journals.db       # SQLite 数据库（去重记录）
└── README.md                 # 项目文档（本文件）
```

### 文件详细说明

#### `requirements.txt` — 依赖管理

```
feedparser       # 解析 RSS/Atom 订阅源
beautifulsoup4   # 清洗 HTML 摘要文本
openai           # 调用 DeepSeek（兼容 OpenAI 接口）的 AI 判断
```

GitHub Actions 在每次运行时执行 `pip install -r requirements.txt`，在临时虚拟机上安装这三个依赖。

#### `main.py` — 核心业务逻辑

包含所有核心函数和配置，详见 [第 5 节](#5-mainpy-业务流程详解)。

#### `.github/workflows/main.yml` — GitHub Actions 配置

定义了**何时**运行、**在哪里**运行、**运行什么**，详见 [第 4 节](#4-yaml-配置详解)。

> ⚠️ **注意：** `main.yml` 不是"用一次就废弃"的文件。每次触发时，GitHub Actions 都会读取它来决定如何执行任务。它是整个自动化系统持续运转的"规则书"。

#### `finance_journals.db` — SQLite 数据库

| 字段 | 类型 | 说明 |
|------|------|------|
| `link` | TEXT (PRIMARY KEY) | 文章 URL，唯一标识 |
| `title` | TEXT | 文章标题 |
| `journal` | TEXT | 来源期刊名称 |
| `published_date` | TEXT | 发布日期 |

**关键机制：** 每次运行结束后，更新的 `.db` 文件会被 `git push` 推回仓库。下次运行时，通过 `Checkout` 步骤重新获取，从而在"临时虚拟机"之间保留状态（去重记录）。

---

## 4. YAML 配置详解

```yaml
name: Monthly Finance Bot          # 工作流名称（显示在 Actions 页面）

on:
  schedule:
    # ┌─── 分钟 (0)
    # │ ┌── 小时 (9, UTC = 北京时间 17:00)
    # │ │ ┌─ 日期 (每月 1 日和 15 日)
    # │ │ │     ┌── 月份 (* = 每月)
    # │ │ │     │ ┌─ 星期 (* = 每天)
    - cron: '0 9 1,15 * *'         # 每月 1 日和 15 日 UTC 09:00 自动运行
  workflow_dispatch:                # 允许在 Actions 页面手动点击"Run workflow"触发

permissions:
  contents: write                   # 赋予工作流写入仓库的权限（用于推送数据库文件）

jobs:
  run_bot:                          # Job 名称
    runs-on: ubuntu-latest          # 在最新版 Ubuntu 虚拟机上运行

    steps:
      # Step 1: 签出代码（将仓库内容复制到虚拟机，包括 finance_journals.db）
      - name: Checkout code
        uses: actions/checkout@v3

      # Step 2: 安装指定版本的 Python
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      # Step 3: 安装项目所需的 Python 库
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      # Step 4: 运行核心脚本，并注入 GitHub Secrets 为环境变量
      - name: Run Bot Script
        env:
          SENDER_EMAIL: ${{ secrets.SENDER_EMAIL }}       # 发件人邮箱
          SENDER_PASSWORD: ${{ secrets.SENDER_PASSWORD }} # 邮箱授权码
          RECEIVER_EMAIL: ${{ secrets.RECEIVER_EMAIL }}   # 收件人邮箱
          # LLM_API_KEY 默认未注入；若需启用 AI 判断，参见第 7 节快速开始指南
        run: python main.py

      # Step 5: 将更新后的数据库文件推送回仓库
      - name: Commit and Push DB changes
        run: |
          git config --global user.name "GitHub Action Bot"
          git config --global user.email "actions@github.com"
          git add finance_journals.db
          git commit -m "Update database records [skip ci]" || exit 0
          git pull --rebase origin main    # 防止并发冲突
          git push
```

### 触发条件说明

| 触发方式 | 描述 | 使用场景 |
|----------|------|---------|
| `schedule` (cron) | 按时间表自动触发 | 每月定期获取新论文 |
| `workflow_dispatch` | 手动点击按钮触发 | 首次测试、临时补充运行 |

### `[skip ci]` 标记

提交信息中包含 `[skip ci]`，是为了防止推送数据库更新后，再次触发 CI 工作流，形成无限循环。

---

## 5. main.py 业务流程详解

### 5.1 配置区域（顶部常量）

```python
# 邮件配置（从 GitHub Secrets 读取）
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL  = os.environ.get("RECEIVER_EMAIL")
LLM_API_KEY     = os.environ.get("LLM_API_KEY")

# SMTP 服务（QQ 邮箱）
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT   = 465

# 关键词白名单（命中即选中，无需 AI 判断）
MUST_HAVE_KEYWORDS = ["fintech", "machine learning", "金融科技", ...]

# AI 判别的用户兴趣描述
USER_INTEREST_DESCRIPTION = "..."

# RSS 订阅源（12 个中英文顶刊）
RSS_FEEDS = {"Journal of Finance": "https://...", ...}

# AI 模型配置
LLM_BASE_URL = "https://api.deepseek.com"
LLM_MODEL    = "deepseek-chat"
DB_FILE      = "finance_journals.db"
```

### 5.2 核心函数说明

| 函数 | 功能 |
|------|------|
| `init_db()` | 初始化 SQLite 数据库，创建 `articles` 表（如已存在则跳过） |
| `is_new(link)` | 检查文章链接是否已存在于数据库（去重判断） |
| `save_article(...)` | 将新文章信息插入数据库（`INSERT OR IGNORE` 防重复） |
| `clean_html(raw)` | 使用 BeautifulSoup 去除摘要中的 HTML 标签 |
| `get_ai_judgement(title, abstract)` | 调用 DeepSeek API 判断论文是否符合兴趣，返回 `True/False` |
| `get_zju_vpn_link(url)` | 将原始链接转换为浙大 WebVPN 格式（方便校内访问） |
| `send_email(subject, html)` | 通过 QQ SMTP 发送 HTML 格式邮件 |
| `run_job()` | 主函数，串联所有步骤 |

### 5.3 过滤逻辑（两道防线）

```
第一道：关键词白名单（速度快，0 费用）
  ↓ 未命中
第二道：AI 判断（DeepSeek API，成本低但有延迟）
  ↓ 宁可多选，不可漏选（宽容策略）
```

### 5.4 邮件内容结构

- 感兴趣的论文（💡 标记）：橙色加粗标题 + 摘要预览
- 普通论文：蓝色标题，无摘要
- 每篇论文附带两个链接：
  - 🏫 浙大 WebVPN 直连（校内机构访问）
  - 🔍 Google Scholar 搜索

---

## 6. 工作流生命周期

### 6.1 首次运行（手动触发/首次 Push）

```
用户操作：
  1. Fork/Clone 仓库
  2. 配置 GitHub Secrets（邮箱、API Key）
  3. 手动触发 workflow_dispatch 或等待定时触发

GitHub Actions 执行：
  虚拟机启动 → Checkout → Setup Python → 安装依赖
  → main.py 运行（数据库为空，所有文章都是"新的"）
  → 发送包含大量文章的邮件
  → 推送初始化后的数据库回仓库
  → 虚拟机销毁
```

### 6.2 后续定时运行

```
每月 1 日 / 15 日 UTC 09:00：
  虚拟机启动 → Checkout（拉取含历史记录的 .db 文件）
  → main.py 运行（数据库已有记录，只推送真正的新文章）
  → 发送增量更新邮件
  → 推送更新的数据库回仓库
  → 虚拟机销毁
```

### 6.3 状态持久化机制

```
┌─────────────────────────────────────────────────────────────┐
│  虽然每次运行都在全新的虚拟机上，但状态通过以下方式保留：       │
│                                                             │
│  finance_journals.db（SQLite 数据库）存储在 GitHub 仓库中   │
│                                                             │
│  每次运行流程：                                              │
│  Checkout → 从仓库拉取 .db → 运行脚本 → 更新 .db → Push 回去│
│                                                             │
│  这样，历史处理记录在"无状态的临时虚拟机"之间得以传递。       │
└─────────────────────────────────────────────────────────────┘
```

### 6.4 `main.yml` 的持续作用

> `main.yml` **不是**"配置一次就废弃"的文件。
>
> 每次工作流被触发时（无论定时还是手动），GitHub Actions 都会**重新读取**这个文件，按照其中定义的步骤执行。它是整个自动化系统的"永久规则书"，只要仓库存在，它就一直有效。

---

## 7. 快速开始指南

### 7.1 前置条件

- 一个 GitHub 账号
- 一个 QQ 邮箱（用于发送邮件，需开启 SMTP 服务）
- （可选）一个 DeepSeek API Key（用于 AI 智能筛选）

### 7.2 配置步骤

**Step 1：Fork 仓库**

点击本仓库右上角的 **Fork** 按钮，将仓库复制到你的账号下。

**Step 2：开启 QQ 邮箱 SMTP**

1. 登录 QQ 邮箱 → **设置** → **账户**
2. 找到 **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务**
3. 开启 **SMTP 服务**，获取**授权码**（不是登录密码）

**Step 3：配置 GitHub Secrets**

进入你 Fork 的仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 名称 | 说明 | 示例 |
|-------------|------|------|
| `SENDER_EMAIL` | 发件人 QQ 邮箱地址 | `12345678@qq.com` |
| `SENDER_PASSWORD` | QQ 邮箱 SMTP 授权码 | `abcdefghijklmnop` |
| `RECEIVER_EMAIL` | 收件人邮箱地址（可与发件人相同） | `yourname@gmail.com` |
| `LLM_API_KEY` | DeepSeek API Key（可选，不填则跳过 AI 判断） | `sk-xxxxxxxx` |

> ⚠️ **注意：** 若要启用 AI 判断，还需在 `main.yml` 的 `Run Bot Script` 步骤的 `env` 部分添加：
> ```yaml
> LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
> ```

**Step 4：手动触发测试**

1. 进入你的仓库 → **Actions** 标签页
2. 点击左侧 **Monthly Finance Bot**
3. 点击右侧 **Run workflow** → **Run workflow**
4. 等待约 2-5 分钟，查看运行日志
5. 检查收件箱是否收到邮件

**Step 5：自定义配置（可选）**

编辑 `main.py` 顶部的配置区域：

```python
# 修改关键词
MUST_HAVE_KEYWORDS = ["你的关键词1", "your keyword2", ...]

# 修改 AI 判别标准
USER_INTEREST_DESCRIPTION = """你的研究方向描述..."""

# 修改运行时间（在 main.yml 中）
- cron: '0 9 1,15 * *'  # 改成你想要的时间
```

---

## 8. 故障排除

### 8.1 常见问题

#### ❓ 工作流运行成功但没有收到邮件

| 可能原因 | 解决方案 |
|---------|---------|
| Secrets 配置错误 | 检查 `SENDER_EMAIL`、`SENDER_PASSWORD`、`RECEIVER_EMAIL` 是否正确填写 |
| QQ 邮箱 SMTP 未开启 | 前往 QQ 邮箱设置开启 SMTP 服务并获取授权码 |
| 邮件被归入垃圾箱 | 检查收件箱的垃圾邮件文件夹 |
| 没有新文章 | 数据库中已有所有文章，无新增内容（正常现象） |

#### ❓ 工作流运行失败（Actions 显示红色 ✗）

| 可能原因 | 解决方案 |
|---------|---------|
| RSS 源暂时不可用 | 点击 **Re-run failed jobs** 重试，或检查期刊网站是否正常 |
| Python 依赖安装失败 | 查看 "Install dependencies" 步骤的日志 |
| 数据库推送冲突 | 工作流会自动 `git pull --rebase` 处理冲突，通常无需手动干预 |

#### ❓ AI 判断不生效（所有文章只走关键词筛选）

检查：
1. `LLM_API_KEY` Secret 是否已添加
2. `main.yml` 的 `env` 部分是否包含 `LLM_API_KEY: ${{ secrets.LLM_API_KEY }}`
3. DeepSeek API 账户余额是否充足

#### ❓ 如何修改运行频率？

编辑 `.github/workflows/main.yml` 中的 `cron` 表达式：

```yaml
# 每周一 UTC 09:00 运行
- cron: '0 9 * * 1'

# 每天 UTC 09:00 运行
- cron: '0 9 * * *'

# 每月 1 日 UTC 09:00 运行
- cron: '0 9 1 * *'
```

> Cron 表达式格式：`分 时 日 月 周`，时区为 UTC（北京时间 = UTC+8）

#### ❓ 如何添加新的期刊？

在 `main.py` 的 `RSS_FEEDS` 字典中添加新条目：

```python
RSS_FEEDS = {
    # 现有期刊...
    "新期刊名称": "https://期刊RSS地址",
}
```

### 8.2 查看运行日志

1. 进入仓库 → **Actions** 标签页
2. 点击最近的运行记录
3. 点击 **run_bot** Job
4. 展开各个 Step 查看详细日志

---

## 许可证

本项目仅供个人学习和研究使用。请遵守各期刊网站的使用条款。