import feedparser
import sqlite3
import smtplib
import os
import sys
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

# ================= 配置区域 =================

# 1. 密码和邮箱从环境变量获取 (GitHub Secrets)
# 不要在代码里直接写密码了！
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465

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
        print("Error: Email credentials not found in environment variables.")
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
    pending_save_list = []

    for journal_name, rss_url in RSS_FEEDS.items():
        print(f"Checking {journal_name}...")
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                continue

            # 抓取前50条
            for entry in feed.entries[:50]: 
                title = entry.title
                link = entry.link
                pub_date = entry.get('published', datetime.now().strftime('%Y-%m-%d'))

                if is_article_new(link):
                    if journal_name not in monthly_data:
                        monthly_data[journal_name] = []
                    
                    article_info = {"title": title, "link": link, "date": pub_date, "journal": journal_name}
                    monthly_data[journal_name].append(article_info)
                    pending_save_list.append(article_info)
                    total_new_count += 1
        except Exception as e:
            print(f"Error checking {journal_name}: {e}")

    if total_new_count > 0:
        print(f"Found {total_new_count} new articles.")
        html_body = f"""
        <html><body>
            <h1 style="color: #2c3e50;">📅 金融顶刊更新汇总</h1>
            <p>本次更新 <b>{total_new_count}</b> 篇文章：</p><hr>
        """
        for journal, articles in monthly_data.items():
            html_body += f"<h3 style='background-color: #f2f2f2; padding: 10px;'>📚 {journal} ({len(articles)}篇)</h3><ul>"
            for art in articles:
                html_body += f"<li style='margin-bottom:8px;'><a href='{art['link']}' style='font-weight:bold;'>{art['title']}</a><br><span style='color:#666;font-size:0.9em;'>{art['date']}</span></li>"
            html_body += "</ul>"
        html_body += "</body></html>"
        
        if send_html_email(f"顶刊更新汇总 ({total_new_count}篇)", html_body):
            print("Saving to DB...")
            for art in pending_save_list:
                save_article(art['link'], art['title'], art['journal'], art['date'])
    else:
        print("No new articles.")

if __name__ == "__main__":
    init_db()
    run_job()
    # 注意：这里去掉了 while True 循环
