import feedparser
import sqlite3
import smtplib
import os
import time
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI

# ================= 配置区域 =================

# 1. 环境变量 (GitHub Secrets)
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")
LLM_API_KEY = os.environ.get("LLM_API_KEY")

SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465

# 2. 🤖 [核心修改] 用自然语言描述你的研究兴趣
# 你可以写得很具体，AI 会理解其中的概念、同义词和隐含逻辑。
USER_INTEREST_DESCRIPTION = """
我的主要研究兴趣是金融科技（FinTech）和机器学习在资产定价中的应用。
具体包括：
1. 深度学习、神经网络、NLP文本分析在预测股票收益率中的应用。
2. 市场微观结构中的高频交易策略。
3. 因果推断和计量方法
"""

# 3. 大模型配置 (这里默认使用 DeepSeek，因为它便宜且强大)
# 如果你想用 ChatGPT，Base_URL 改为 "https://api.openai.com/v1", Model 改为 "gpt-4o-mini"
LLM_BASE_URL = "https://api.deepseek.com" 
LLM_MODEL = "deepseek-chat"

# 4. RSS 列表
RSS_FEEDS = {
    "Journal of Finance": "https://onlinelibrary.wiley.com/feed/15406261/most-recent",
    "JFE": "https://www.sciencedirect.com/science/journal/0304405X/rss", 
    "RFS": "https://academic.oup.com/rss/site_5378/3126.xml",
    "JFQA": "https://www.cambridge.org/core/rss/product/id/1638F6E6C5C0F911299901594F817173",
    "Management Science": "http://pubsonline.informs.org/action/showFeed?type=etoc&feed=rss&jc=mnsc",
    "Review of Finance": "https://academic.oup.com/rss/site_5409/3133.xml"
}

DB_FILE = "finance_journals.db"

# ================= 核心代码 =================

def get_ai_judgement(title, abstract):
    """调用 LLM 判断文章是否符合兴趣"""
    if not LLM_API_KEY:
        print("Error: No API Key found.")
        return False

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    
    # 构造 Prompt
    prompt = f"""
    你是一个专业的金融学术助手。请根据以下用户的研究兴趣描述，判断给定的一篇论文是否值得推荐给用户。
    
    【用户研究兴趣】：
    {USER_INTEREST_DESCRIPTION}
    
    【论文标题】：{title}
    【论文摘要】：{abstract}
    
    请只回答 "Yes" 或 "No"。如果论文的主题、方法或核心概念与用户的兴趣高度相关（包括概念上的相关性），回答 "Yes"，否则回答 "No"。不要输出任何其他解释。
    """

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, # 低温度保证回答稳定
            max_tokens=5
        )
        answer = response.choices[0].message.content.strip().lower()
        return "yes" in answer
    except Exception as e:
        print(f"AI Check Error: {e}")
        # 如果AI报错（比如网络问题），默认放行或者设为False，这里设为False防止乱发
        return False

def clean_html_text(raw_html):
    if not raw_html: return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=' ')
    return ' '.join(text.split())

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS articles
                 (link TEXT PRIMARY KEY, title TEXT, journal TEXT, published_date TEXT)''')
    conn.commit()
    conn.close()

def is_article_new(link):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM articles WHERE link=?", (link,))
    exists = c.fetchone()
    conn.close()
    return exists is None

def save_article(link, title, journal, pub_date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO articles VALUES (?, ?, ?, ?)", (link, title, journal, pub_date))
    conn.commit()
    conn.close()

def send_html_email(subject, html_content):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return False
    msg = MIMEText(html_content, 'html', 'utf-8')
    msg['From'] = Header(SENDER_EMAIL)
    msg['To'] = Header(RECEIVER_EMAIL)
    msg['Subject'] = Header(subject, 'utf-8')
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
        server.quit()
        print("Email sent successfully.")
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

def run_job():
    print(f"[{datetime.now()}] Job started...")
    
    monthly_data = {}
    total_new_count = 0
    interesting_count = 0
    pending_save_list = []

    for journal_name, rss_url in RSS_FEEDS.items():
        print(f"Checking {journal_name}...")
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries: continue

            # 为了节省Token和时间，限制每次最多检查前30篇
            for entry in feed.entries[:30]: 
                title = entry.title
                link = entry.link
                pub_date = entry.get('published', datetime.now().strftime('%Y-%m-%d'))
                
                # 只有当文章是新的才去调用AI检查（省钱、省时间）
                if is_article_new(link):
                    raw_summary = entry.get('summary') or entry.get('description') or ""
                    clean_summary = clean_html_text(raw_summary)

                    # === 调用 AI 进行智能判断 ===
                    # 打印一下正在检查哪篇，方便在 GitHub Log 里看
                    print(f"Analyzing with AI: {title[:50]}...") 
                    is_interesting = get_ai_judgement(title, clean_summary)
                    time.sleep(0.2) # 稍微歇一下，防止API速率限制
                    
                    if journal_name not in monthly_data:
                        monthly_data[journal_name] = []
                    
                    article_info = {
                        "title": title,
                        "link": link,
                        "date": pub_date,
                        "journal": journal_name,
                        "summary": clean_summary,
                        "is_interesting": is_interesting
                    }
                    
                    if is_interesting:
                        monthly_data[journal_name].insert(0, article_info)
                        interesting_count += 1
                        print(f"  >>> MATCH FOUND: {title[:30]}")
                    else:
                        monthly_data[journal_name].append(article_info)
                        
                    pending_save_list.append(article_info)
                    total_new_count += 1
        except Exception as e:
            print(f"Error checking {journal_name}: {e}")

    if total_new_count > 0:
        print(f"Found {total_new_count} new articles ({interesting_count} AI-Matched).")
        
        subject_prefix = "🤖 " if interesting_count > 0 else ""
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #2c3e50;">📅 金融顶刊 AI 筛选汇总</h2>
            <p>本次更新 <b>{total_new_count}</b> 篇文章，AI 助手为您识别出 <b>{interesting_count}</b> 篇相关文章。</p>
            <div style="background-color: #e8f4fd; padding: 10px; border-radius: 5px; color: #555; font-size: 0.9em; margin-bottom: 20px;">
                <b>您的筛选标准:</b><br>{USER_INTEREST_DESCRIPTION.replace(chr(10), '<br>')}
            </div>
            <hr>
        """
        
        for journal, articles in monthly_data.items():
            html_body += f"<h3 style='background-color: #f2f2f2; padding: 10px; border-left: 5px solid #0066cc;'>📚 {journal} ({len(articles)}篇)</h3><ul>"
            for art in articles:
                if art['is_interesting']:
                    icon = "💡" # AI 推荐的图标
                    title_style = "color: #d35400; font-weight: bold; font-size: 1.1em;"
                    # AI 推荐的文章，显示摘要
                    summary_html = f"<div style='background-color: #fff8f0; padding: 10px; margin-top: 5px; border-radius: 5px; color: #444; font-size: 0.9em; line-height: 1.5;'>{art['summary'][:600]}...</div>"
                else:
                    icon = ""
                    title_style = "color: #0066cc; font-weight: bold;"
                    summary_html = "" # 普通文章不显示摘要

                html_body += f"""
                <li style="margin-bottom: 20px;">
                    {icon} <a href="{art['link']}" style="{title_style} text-decoration: none;">{art['title']}</a>
                    <span style="color: #999; font-size: 0.85em; margin-left: 10px;">{art['date']}</span>
                    {summary_html}
                </li>
                """
            html_body += "</ul>"
        
        html_body += "</body></html>"
        
        if send_html_email(f"{subject_prefix}AI精选顶刊: {interesting_count}/{total_new_count}篇", html_body):
            print("Saving to DB...")
            for art in pending_save_list:
                save_article(art['link'], art['title'], art['journal'], art['date'])
    else:
        print("No new articles.")

if __name__ == "__main__":
    init_db()
    run_job()
