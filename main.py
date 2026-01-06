import feedparser
import sqlite3
import smtplib
import os
import time
import ssl
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI

# ================= 配置区域 =================

# 1. 环境变量
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")
LLM_API_KEY = os.environ.get("LLM_API_KEY")
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465

# 2. 🛡️ 【白名单兜底】中英文关键词 (不区分大小写)
MUST_HAVE_KEYWORDS = [
    # --- English ---
    "fintech", "financial technology", 
    "machine learning", "deep learning", "neural network",
    "climate risk", "esg", "textual analysis",
    # --- 中文 ---
    "金融科技", "机器学习", "深度学习", "神经网络", "文本分析",
     "大语言模型", "高频交易", "量化投资"
]

# 3. 🤖 【AI 判别标准】
USER_INTEREST_DESCRIPTION = """
我的研究兴趣非常广泛，请采取【宽容策略】，只要文章符合以下**任意一个**方向，都回答 Yes：

1. **金融科技 (FinTech)**：涉及高频交易、市场微观结构、支付、区块链、数字货币及货币理论的任何话题。
2. **AI与大数据**：金融中的机器学习、NLP文本分析、情感分析、高维数据预测。
3. **资产定价**：股票收益预测、因子模型、量化策略。
4. **计量**：因果推断模型、计量模型。

注意：
- 对于中文文章，请同样应用上述标准。
- 如果没有摘要，仅根据标题判断。
"""

# 4. 📚 期刊 RSS 列表
RSS_FEEDS = {
    # === 英文 Top Journals ===
    "Journal of Finance": "https://onlinelibrary.wiley.com/feed/15406261/most-recent",
    "JFE": "https://www.sciencedirect.com/science/journal/0304405X/rss", 
    "RFS": "https://academic.oup.com/rss/site_5378/3126.xml",
    "JFQA": "https://www.cambridge.org/core/rss/product/id/1638F6E6C5C0F911299901594F817173",
    "Management Science": "http://pubsonline.informs.org/action/showFeed?type=etoc&feed=rss&jc=mnsc",
    "Review of Finance": "https://academic.oup.com/rss/site_5409/3133.xml",
    
    # === 中文 Top Journals (via RSSHub) ===
    "经济研究": "https://rsshub.app/cnki/journals/JJYJ",
    "管理世界": "https://rsshub.app/cnki/journals/GLSJ",
    "金融研究": "https://rsshub.app/cnki/journals/JRYJ",
    "数量经济技术经济研究": "https://rsshub.app/cnki/journals/SLJY",
    "中国工业经济": "https://rsshub.app/cnki/journals/GGYY",
    "经济学季刊": "https://rsshub.app/cnki/journals/JJXJ"
}

LLM_BASE_URL = "https://api.deepseek.com" 
LLM_MODEL = "deepseek-chat"
DB_FILE = "finance_journals.db"

# ================= 核心代码 =================

def get_ai_judgement(title, abstract):
    if not LLM_API_KEY: return False
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    
    prompt = f"""
    判断这篇金融论文是否符合用户兴趣。
    
    【用户兴趣】：{USER_INTEREST_DESCRIPTION}
    
    【论文标题】：{title}
    【论文摘要】：{abstract}
    
    规则：
    1. 宁可错杀一千，不可放过一个。只要有一点点相关性，就回答 "Yes"。
    2. 对于中文标题，请理解其语义。
    3. 只回答 "Yes" 或 "No"。
    """
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=5
        )
        return "yes" in response.choices[0].message.content.strip().lower()
    except:
        return False

def clean_html(raw):
    if not raw: return ""
    text = BeautifulSoup(raw, "html.parser").get_text(separator=' ')
    return ' '.join(text.split())

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''CREATE TABLE IF NOT EXISTS articles (link TEXT PRIMARY KEY, title TEXT, journal TEXT, published_date TEXT)''')
    conn.close()

def is_new(link):
    conn = sqlite3.connect(DB_FILE)
    exists = conn.execute("SELECT 1 FROM articles WHERE link=?", (link,)).fetchone()
    conn.close()
    return exists is None

def save_article(link, title, journal, pub_date):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT OR IGNORE INTO articles VALUES (?, ?, ?, ?)", (link, title, journal, pub_date))
    conn.commit()
    conn.close()

def send_email(subject, html):
    if not SENDER_PASSWORD: return False
    msg = MIMEText(html, 'html', 'utf-8')
    msg['From'], msg['To'], msg['Subject'] = Header(SENDER_EMAIL), Header(RECEIVER_EMAIL), Header(subject, 'utf-8')
    try:
        s = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        s.login(SENDER_EMAIL, SENDER_PASSWORD)
        s.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
        s.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

def run_job():
    print("Job started...")
    monthly_data = {}
    total_new = 0
    interesting_count = 0
    pending_save = []

    # 忽略 SSL 证书验证
    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context

    # 【新增】伪装成 Chrome 浏览器，防止被拦截 (解决 No entries 问题)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for journal, url in RSS_FEEDS.items():
        print(f"Checking {journal}...")
        try:
            # 传入 request_headers
            feed = feedparser.parse(url, request_headers=headers)
            
            if not feed.entries:
                print(f"  > Warning: No entries for {journal}")
                continue

            for entry in feed.entries[:20]: 
                title = entry.title
                link = entry.link
                date = datetime.now().strftime('%Y-%m-%d')
                if 'published' in entry:
                    try: date = entry.published[:10]
                    except: pass
                
                if is_new(link):
                    # 1. 关键词白名单检查
                    is_match = False
                    for kw in MUST_HAVE_KEYWORDS:
                        if kw.lower() in title.lower():
                            is_match = True
                            print(f"  >>> [Keyword Match] {title[:30]}...")
                            break
                    
                    summary = clean_html(entry.get('summary') or entry.get('description'))
                    
                    # 2. AI 检查
                    if not is_match:
                        print(f"  ...asking AI: {title[:30]}...")
                        is_match = get_ai_judgement(title, summary)
                        time.sleep(0.2) # 防止 API 超速

                    if journal not in monthly_data: monthly_data[journal] = []
                    
                    # 【关键修复】补全 info 字典，加入 journal 字段
                    info = {
                        "title": title, 
                        "link": link, 
                        "date": date, 
                        "summary": summary, 
                        "is_interesting": is_match,
                        "journal": journal  # 之前报错是因为缺了这个
                    }
                    
                    if is_match:
                        monthly_data[journal].insert(0, info)
                        interesting_count += 1
                    else:
                        monthly_data[journal].append(info)
                    
                    pending_save.append(info)
                    total_new += 1
        except Exception as e:
            print(f"Error checking {journal}: {e}")

    if total_new > 0:
        print(f"Found {total_new} articles, {interesting_count} interesting.")
        subject_icon = "🤖 " if interesting_count > 0 else ""
        
        html = f"""<html><body style="font-family:Arial;">
        <h2>📅 顶刊文献更新 (中英文混排)</h2>
        <div style="background:#e8f4fd;padding:10px;margin-bottom:20px;border-radius:5px;">
        <b>筛选策略：</b>包含 FinTech/机器学习/计量 等中英文关键词，或经 AI 判定符合兴趣。
        </div><hr>"""
        
        for journal, arts in monthly_data.items():
            html += f"<h3 style='background:#f2f2f2;padding:10px;border-left:5px solid #0066cc;'>{journal}</h3><ul>"
            for art in arts:
                if art['is_interesting']:
                    style = "color:#d35400;font-weight:bold;font-size:1.1em;"
                    summ = f"<div style='background:#fff8f0;padding:8px;margin-top:5px;color:#555;font-size:0.9em;'>{art['summary'][:300]}...</div>"
                    icon = "💡"
                else:
                    style, summ, icon = "color:#0066cc;font-weight:bold;", "", ""
                
                html += f"<li style='margin-bottom:15px;'>{icon} <a href='{art['link']}' style='{style}text-decoration:none;'>{art['title']}</a><span style='color:#999;font-size:0.8em;margin-left:10px;'>{art['date']}</span>{summ}</li>"
            html += "</ul>"
        
        html += "</body></html>"

        if send_email(f"{subject_icon}文献更新: {interesting_count}篇精选 ({total_new}篇新增)", html):
            for art in pending_save: 
                # 这里现在不会报错了
                save_article(art['link'], art['title'], art['journal'], art['date'])
            
            # 自动同步数据库
            os.system('git config --global user.name "Bot" && git config --global user.email "bot@bot.com"')
            os.system('git add finance_journals.db && git commit -m "Update DB" && git pull --rebase origin main && git push')
    else:
        print("No new articles.")

if __name__ == "__main__":
    init_db()
    run_job()
