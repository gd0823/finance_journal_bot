# 📰 Finance Journal Bot — 财经论文订阅机器人

> 一个全自动的财经学术论文追踪器：定期抓取顶级期刊 RSS 源，通过关键词与 AI 双重筛选，自动发送邮件摘要，并将记录持久化到本地数据库。

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📖 项目概述

**Finance Journal Bot** 是一个运行在 GitHub Actions 上的自动化学术论文订阅机器人。它能够：

- 🔍 **定期抓取**：从 Journal of Finance、JFE、RFS 等英文顶刊及经济研究、金融研究等中文顶刊的 RSS 源获取最新论文
- 🏷️ **关键词过滤**：根据预设关键词（FinTech、机器学习、ESG 等）进行初步筛选
- 🤖 **AI 智能判别**：调用 DeepSeek / OpenAI GPT，根据用户兴趣描述进行二次智能筛选
- 📧 **邮件通知**：将筛选结果以 HTML 格式发送到指定邮箱，包含浙大 WebVPN 直连和 Google Scholar 链接
- 🗄️ **去重持久化**：将已处理论文保存到 SQLite 数据库，避免重复推送

---

## 🔄 完整工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    第一次手动操作（初始化）                        │
│                                                                  │
│  你的本地电脑                                                     │
│  ┌──────────────┐                                               │
│  │  创建所有文件  │  git push  ┌──────────────────────────────┐ │
│  │  main.py     │ ─────────► │     GitHub 云端仓库            │ │
│  │  main.yml    │            │  扫描 .github/workflows/ 目录  │ │
│  │  requirements│            │  读取并记住 main.yml 配置       │ │
│  └──────────────┘            └──────────────┬───────────────┘ │
│                                              │                   │
│                              "从此刻起，GitHub 知道了要做什么"    │
└──────────────────────────────────────────────┼──────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    后续定期自动执行（循环）                        │
│                                                                  │
│   ⏰ GitHub 定时器 (cron: '0 9 1,15 * *')                        │
│        │                                                         │
│        │  每月 1 号和 15 号 UTC 09:00 (北京时间 17:00)            │
│        ▼                                                         │
│   🖥️ 启动全新虚拟机 (ubuntu-latest)                              │
│        │                                                         │
│        ├── ① checkout 拉取最新代码                               │
│        ├── ② 安装 Python 3.9 + 依赖包                           │
│        ├── ③ 运行 main.py                                       │
│        │      ├── 抓取各期刊 RSS 源                              │
│        │      ├── 关键词过滤                                     │
│        │      ├── AI 智能判别 (DeepSeek API)                     │
│        │      ├── 发送 HTML 邮件                                 │
│        │      └── 写入 SQLite 数据库                             │
│        ├── ④ 提交并推送更新的数据库文件                           │
│        │                                                         │
│        ▼                                                         │
│   🗑️ 虚拟机立即销毁（什么都不留下）                               │
│        │                                                         │
│        └── 等待下次触发 → 重复上述循环                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构与文件功能

```
finance_journal_bot/
├── README.md                          # 项目文档（本文件）
├── requirements.txt                   # Python 依赖包列表
├── main.py                            # 核心业务逻辑脚本
├── finance_journals.db                # SQLite 数据库（存储已处理论文）
└── .github/
    └── workflows/
        └── main.yml                   # GitHub Actions 工作流配置
```

### 1. `requirements.txt` — Python 依赖

| 依赖包 | 用途 |
|--------|------|
| `feedparser` | 解析各期刊的 RSS/Atom 订阅源，提取论文标题、链接、摘要等信息 |
| `beautifulsoup4` | 清洗 RSS 条目中的 HTML/XML 标签，提取纯文本摘要 |
| `openai` | 调用 OpenAI/DeepSeek 兼容 API，对论文进行 AI 智能判别 |

### 2. `main.py` — 核心业务逻辑

主脚本，包含全部业务逻辑，从 RSS 抓取到邮件发送的完整流程。

**主要函数一览：**

| 函数 | 功能 |
|------|------|
| `init_db()` | 初始化 SQLite 数据库，创建 `articles` 表 |
| `is_new(link)` | 检查该论文链接是否已存在于数据库中（去重） |
| `save_article(...)` | 将新论文信息保存到数据库 |
| `clean_html(raw)` | 使用 BeautifulSoup 清洗 HTML 标签，返回纯文本 |
| `get_ai_judgement(title, abstract)` | 调用 LLM API，根据用户兴趣描述判断论文是否符合 |
| `get_zju_vpn_link(url)` | 将论文链接转换为浙大 WebVPN 格式，方便校内访问 |
| `send_email(subject, html)` | 通过 QQ 邮箱 SMTP_SSL 发送 HTML 格式邮件 |
| `run_job()` | 主入口：遍历所有期刊、筛选、构建邮件、发送、保存 |

### 3. `.github/workflows/main.yml` — 自动化配置

GitHub Actions 工作流定义文件，是整个自动化机制的"合同书"。

### 4. `finance_journals.db` — SQLite 数据库

本地持久化存储，记录所有已处理论文的链接，防止重复推送。每次执行后会提交回 GitHub 仓库保存。

---

## ⚙️ YAML 配置详解

```yaml
name: Monthly Finance Bot       # 工作流名称（显示在 GitHub Actions 页面）

on:
  schedule:
    # ┌──── 分钟 (0-59)
    # │ ┌─── 小时 (0-23, UTC 时间)
    # │ │ ┌── 日 (1-31)
    # │ │ │    ┌─ 月 (1-12)
    # │ │ │    │ ┌ 星期 (0-6, 0=周日)
    # │ │ │    │ │
    - cron: '0 9 1,15 * *'   # 每月1号和15号 UTC 09:00 (北京时间 17:00) 自动触发
  workflow_dispatch:           # 允许在 GitHub 网页上手动点击"Run workflow"触发

permissions:
  contents: write              # 赋予工作流写入仓库的权限（用于推回更新的数据库文件）

jobs:
  run_bot:                     # Job 名称（可自定义）
    runs-on: ubuntu-latest     # 在 GitHub 提供的最新 Ubuntu 虚拟机上运行

    steps:
    # Step 1: 将仓库代码拉取到虚拟机
    - name: Checkout code
      uses: actions/checkout@v3

    # Step 2: 安装 Python 3.9 环境
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    # Step 3: 安装 requirements.txt 中列出的所有依赖
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    # Step 4: 运行主脚本（通过 Secrets 注入敏感配置）
    - name: Run Bot Script
      env:
        SENDER_EMAIL: ${{ secrets.SENDER_EMAIL }}       # 发件人邮箱
        SENDER_PASSWORD: ${{ secrets.SENDER_PASSWORD }} # 邮箱密码/应用密码
        RECEIVER_EMAIL: ${{ secrets.RECEIVER_EMAIL }}   # 收件人邮箱
      run: python main.py

    # Step 5: 将更新的数据库文件提交并推回仓库
    - name: Commit and Push DB changes
      run: |
        git config --global user.name "GitHub Action Bot"
        git config --global user.email "actions@github.com"
        git add finance_journals.db
        git commit -m "Update database records [skip ci]" || exit 0
        git pull --rebase origin main   # 先拉取最新，避免冲突
        git push                         # 推送更新的数据库
```

---

## 🐍 `main.py` 业务逻辑详解

### 环境变量配置

```python
# 从 GitHub Secrets 读取，不在代码中硬编码任何密钥
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")  # QQ 邮箱应用专用密码
RECEIVER_EMAIL  = os.environ.get("RECEIVER_EMAIL")
LLM_API_KEY     = os.environ.get("LLM_API_KEY")      # DeepSeek / OpenAI API Key

SMTP_SERVER = "smtp.qq.com"
SMTP_PORT   = 465  # QQ 邮箱 SSL 端口
```

### 关键词过滤列表

```python
# 包含任意一个关键词 → 直接标记为"感兴趣"，跳过 AI 判别（节省 API 费用）
MUST_HAVE_KEYWORDS = [
    "fintech", "financial technology",
    "machine learning", "deep learning", "neural network",
    "climate risk", "esg", "textual analysis",
    "金融科技", "机器学习", "深度学习", "神经网络", "文本分析",
    "大语言模型", "高频交易", "量化投资"
]
```

### AI 判别提示词

```python
# 发送给 LLM 的判别标准，采用"宽容策略"，宁可多选不漏
USER_INTEREST_DESCRIPTION = """
我的研究兴趣非常广泛，请采取【宽容策略】，只要文章符合以下任意一个方向，都回答 Yes：
1. 金融科技 (FinTech)：高频交易、市场微观结构、支付、区块链、数字货币
2. AI与大数据：机器学习、NLP文本分析、情感分析、高维数据预测
3. 资产定价：股票收益预测、因子模型、量化策略
4. 计量：因果推断模型、计量模型
"""
```

### RSS 期刊列表

```python
RSS_FEEDS = {
    # 英文顶刊
    "Journal of Finance": "https://onlinelibrary.wiley.com/feed/15406261/most-recent",
    "JFE":                "https://www.sciencedirect.com/science/journal/0304405X/rss",
    "RFS":                "https://academic.oup.com/rss/site_5378/3126.xml",
    # ... 更多期刊
    
    # 中文顶刊（通过 RSSHub）
    "经济研究": "https://rsshub.app/cnki/journals/JJYJ",
    "金融研究": "https://rsshub.app/cnki/journals/JRYJ",
    # ... 更多期刊
}
```

### 核心函数流程

```
run_job() 执行流程：
│
├── 遍历每个期刊 RSS_FEEDS
│   ├── feedparser.parse(url) 抓取 RSS 源
│   ├── 对每篇论文（最多20篇）：
│   │   ├── is_new(link)?  → 数据库去重检查
│   │   ├── 关键词检查    → 任意命中 → is_match = True
│   │   └── AI 判别       → LLM 返回 "Yes" → is_match = True
│   └── 将论文及筛选结果存入 monthly_data
│
├── 构建 HTML 邮件
│   ├── 感兴趣的论文：橙色加粗，显示摘要前300字
│   ├── 普通论文：蓝色普通
│   └── 每篇附带：原始链接 | 浙大WebVPN链接 | Google Scholar链接
│
├── send_email() 发送邮件
└── save_article() 批量保存到数据库
```

---

## 🎯 工作流生命周期 — 关键部分！

### 第一次手动操作（初始化）

```
你的电脑                          GitHub 云端
─────────                        ─────────────────────────
1. 创建 main.py                  
2. 创建 main.yml                 
3. 创建 requirements.txt         
4. git push ──────────────────► 5. 接收代码
                                 6. 扫描 .github/workflows/
                                 7. 发现并读取 main.yml
                                 8. ✅ 记住所有配置
                                    "我知道要在每月1号和15号运行了"
```

### 后续定期自动执行

```
每月 1 号 UTC 09:00：

GitHub 定时器 ──触发──► 启动虚拟机 ──执行──► 销毁虚拟机
     ⏰                    🖥️                    🗑️
     │                     │
     │                     ├── checkout 代码
     │                     ├── pip install
     │                     ├── python main.py
     │                     │      抓RSS → 筛选 → 发邮件 → 存DB
     │                     └── git push DB 文件
     │
     └── 等待下次触发（15号再来）
```

### ✅ YAML 的持续作用 — 核心理解！

> 💡 **这是最容易误解的地方，请仔细阅读！**

| 误解 ❌ | 正确理解 ✅ |
|---------|-----------|
| "YAML 只在第一次 push 时有用" | YAML 永久保存在 GitHub 云端，每次执行前都重新读取 |
| "push 之后 YAML 就废了" | YAML 是持续生效的"合同"，GitHub 每次都遵照执行 |
| "虚拟机一直在运行" | 虚拟机只在执行时启动，完成后立即销毁 |
| "需要定期重新 push 来激活" | 不需要！一次 push 后自动永久生效 |

**关键要点：**
- ✅ YAML 一旦 push 到 GitHub，就**永久保存在云端**
- ✅ YAML **不是"只用一次就废弃"**的临时配置
- ✅ GitHub **每次触发前都会重新读取**最新的 YAML
- ✅ YAML 是**"你和 GitHub 云端的对话语言"**
- ✅ YAML **定义了"什么时候运行、运行什么、怎么运行"**
- ✅ 如果你**修改 YAML 并 push**，下次执行就会按**新配置**运行

### 🎭 一个直觉的比喻

```
YAML 文件   =  合同书
              （一旦签署就永久有效，双方都必须遵守）

GitHub      =  忠实的员工
              （每次按照最新合同执行，不会忘记也不会偷懒）

Cron 表达式 =  闹钟 / 警钟
              （时间到了就叫醒员工去执行合同）

虚拟机      =  一次性的工作台
              （每次搭建，用完即拆，干净整洁）
```

### 🖥️ 虚拟机的临时特性

```
第1次触发（1月1日）:
  ┌──────────────────────────────┐
  │  全新虚拟机（空白状态）        │
  │  ✓ 安装 Python               │
  │  ✓ 安装 feedparser 等         │
  │  ✓ 运行 main.py              │
  │  ✓ 推送更新的数据库           │
  └──────────────────────────────┘
              ↓ 立即销毁

第2次触发（1月15日）:
  ┌──────────────────────────────┐
  │  全新虚拟机（重新空白状态）    │  ← 不记得上次的任何状态！
  │  ✓ 安装 Python               │     但数据库已 push 到 GitHub
  │  ✓ checkout 含DB的最新代码   │  ← 所以能获取上次的记录
  │  ✓ 运行 main.py              │
  └──────────────────────────────┘
              ↓ 立即销毁
```

> 🔑 **关键**：数据库 `finance_journals.db` 每次执行后都被推送到 GitHub，下次虚拟机 checkout 代码时就能获取。这是跨执行保持"记忆"的方式。

---

## 🚀 快速开始指南

### 前置条件

- ✅ GitHub 账户
- ✅ Python 3.9+（本地测试用）
- ✅ QQ 邮箱账号（建议开启应用专用密码）
- ✅ DeepSeek 或 OpenAI API 密钥（可选，用于 AI 判别）

### 配置步骤（约 5 分钟）

#### 第一步：Fork 或 Clone 此仓库

```bash
git clone https://github.com/gd0823/finance_journal_bot.git
cd finance_journal_bot
```

#### 第二步：修改 `main.py` 中的配置

```python
# 根据你的研究兴趣修改关键词
MUST_HAVE_KEYWORDS = [
    "fintech", "machine learning",   # 保留或修改
    "你的关键词1", "你的关键词2",     # 添加你关心的领域
]

# 修改 AI 判别的兴趣描述
USER_INTEREST_DESCRIPTION = """
我的研究兴趣是...（用自然语言描述你感兴趣的方向）
"""

# 添加或删除期刊 RSS 源
RSS_FEEDS = {
    "Journal of Finance": "https://...",   # 保留
    "你的期刊": "https://...",              # 添加
}
```

#### 第三步：在 GitHub 仓库设置中添加 Secrets

进入仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 名称 | 说明 | 示例 |
|-------------|------|------|
| `SENDER_EMAIL` | 发件人邮箱地址 | `yourname@qq.com` |
| `SENDER_PASSWORD` | QQ 邮箱应用专用密码（非登录密码） | `abcdefghijklmnop` |
| `RECEIVER_EMAIL` | 接收论文摘要的邮箱 | `yourname@gmail.com` |
| `LLM_API_KEY` | DeepSeek 或 OpenAI API 密钥 | `sk-...` |

> 💡 **QQ 邮箱应用专用密码**：登录 QQ 邮箱 → 设置 → 账户 → POP3/SMTP 服务 → 开启 → 生成授权码

#### 第四步：提交代码

```bash
git add .
git commit -m "Initial setup"
git push origin main
```

#### 第五步（可选）：手动测试

进入 GitHub 仓库 → **Actions** → **Monthly Finance Bot** → **Run workflow** → 点击绿色按钮

---

## 🔧 故障排除

### ❓ Workflow 没有运行？

```
检查清单：
□ .github/workflows/main.yml 文件存在且语法正确
□ GitHub Actions 是否被禁用？（仓库 Settings → Actions → 检查是否允许）
□ cron 时间是否已过？（UTC 时间，注意时区换算）
□ 进入 Actions 页面查看是否有错误日志
```

### ❓ 邮件没有收到？

```
检查清单：
□ SENDER_EMAIL / SENDER_PASSWORD / RECEIVER_EMAIL Secrets 是否正确设置
□ QQ 邮箱是否开启了 SMTP 服务
□ 使用的是应用专用密码，不是 QQ 登录密码
□ 查看 Actions 日志中是否有 "Email Error:" 信息
□ 检查垃圾邮件文件夹
```

### ❓ 数据库相关错误？

```
检查清单：
□ workflow permissions 是否设置了 contents: write
□ finance_journals.db 是否已被 git 跟踪（首次运行前需要先 commit 一个空的 DB）
□ 查看 "Commit and Push DB changes" 步骤的日志
```

### ❓ API 调用失败？

```
检查清单：
□ LLM_API_KEY Secret 是否正确设置
□ API 密钥是否有余额
□ LLM_BASE_URL 和 LLM_MODEL 是否匹配你的 API 服务商
□ 即使 AI 调用失败，关键词过滤仍会正常工作
```

---

## 📊 完整时间轴示例

```
2024年12月20日  你 push 代码到 GitHub
                └── GitHub 记住 main.yml 配置 ✅

2025年01月01日  UTC 09:00
                ├── 虚拟机启动
                ├── 抓取到 47 篇新论文
                ├── 关键词命中 8 篇
                ├── AI 判别额外发现 3 篇
                ├── 发送邮件："11篇精选 (47篇新增)"
                ├── 数据库更新并推回 GitHub
                └── 虚拟机销毁

2025年01月15日  UTC 09:00
                ├── 全新虚拟机启动
                ├── checkout 含最新数据库的代码
                ├── 抓取到 32 篇论文（已有47篇记录，不重复）
                ├── 关键词命中 5 篇，AI 发现 2 篇
                ├── 发送邮件："7篇精选 (32篇新增)"
                ├── 数据库更新（现有 79 条记录）
                └── 虚拟机销毁

2025年02月01日  UTC 09:00
                └── ... 重复上述循环，持续进行 ...
```

---

## 🎓 原理解释

### YAML 为什么一直有用？

```
传统想法（错误）：
  push YAML ─► GitHub 读取一次 ─► 执行 ─► YAML 没用了

实际原理（正确）：
  push YAML ─► GitHub 永久保存 ─► 每次触发前重新读取 YAML ─► 执行
                    ↑                        │
                    └────────────────────────┘
                         YAML 一直在那里！
```

### GitHub Actions 如何工作？

```
GitHub 服务器内部有一个"事件监听器"：

while True:
    if current_time matches any cron_expression_in_any_repo:
        trigger_workflow(repo, yaml_config)
    if user_clicked_run_workflow_button:
        trigger_workflow(repo, yaml_config)
    sleep(60 seconds)
```

### Cron 表达式解读

```
cron: '0 9 1,15 * *'
       │ │ │    │ │
       │ │ │    │ └── 星期（* = 任意）
       │ │ │    └──── 月份（* = 任意月）
       │ │ └──────── 日期（1,15 = 1号和15号）
       │ └────────── 小时（9 = UTC 09:00 = 北京时间 17:00）
       └──────────── 分钟（0 = 整点）
```

### 虚拟机如何管理数据？

```
数据持久化策略：

  执行1 ──► 写入 DB ──► git push DB ──► GitHub 仓库
                                            │
  执行2 ──► git checkout ◄── 含最新DB ──────┘
         └── 读取 DB（包含执行1的记录）
         └── 写入新记录
         └── git push DB
```

---

## 📝 许可证与贡献

### 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

### 贡献指南

欢迎提交 Issue 或 Pull Request！

- 🐛 **Bug 报告**：请在 Issues 中提供详细的错误日志
- ✨ **新功能建议**：描述使用场景和预期行为
- 📖 **文档改进**：直接提交 PR 修改 README

### 常见定制需求

| 定制项 | 修改位置 |
|--------|---------|
| 添加新期刊 | `main.py` 中的 `RSS_FEEDS` 字典 |
| 修改筛选关键词 | `main.py` 中的 `MUST_HAVE_KEYWORDS` 列表 |
| 修改 AI 判别标准 | `main.py` 中的 `USER_INTEREST_DESCRIPTION` |
| 修改执行频率 | `main.yml` 中的 `cron` 表达式 |
| 更换 LLM 模型 | `main.py` 中的 `LLM_BASE_URL` 和 `LLM_MODEL` |
| 更换邮件服务商 | `main.py` 中的 `SMTP_SERVER` 和 `SMTP_PORT` |

---

<div align="center">
  <sub>Built with ❤️ using GitHub Actions + Python + DeepSeek AI</sub>
</div>