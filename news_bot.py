import asyncio
import os
import csv
import time
import telegram
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# 보안을 위해 깃허브 설정값에서 가져옵니다
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
bot = telegram.Bot(token=TELEGRAM_TOKEN)

companies = ["더즌", "dozn", "카카오뱅크", "카카오페이", "오픈에셋", "스위치원"]
exceptionalWords = ['랭키파이', '보호자', '브랜드평판', '브랜드 평판', '트렌드지수', '트렌드 지수', '링크드인']
exceptionalSites = ['n.news.naver.com', 'www.pinpointnews.co.kr', 'www.pointdaily.co.kr', 'cwn.kr', 'www.stardailynews.co.kr', 'www.raonnews.com']

csv_file = 'sent_news.csv'

def load_sent_articles():
    if not os.path.exists(csv_file): return set()
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        return set(row[0] for row in reader)

def save_sent_article(url, title):
    with open(csv_file, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([url, title])

def create_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

async def news_release():
    sent_urls = load_sent_articles()
    driver = create_driver()
    for company in companies:
        search_url = f'https://search.naver.com/search.naver?where=news&query="{company}"&sm=tab_opt&sort=1'
        driver.get(search_url)
        time.sleep(2) 
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        news_anchors = soup.select('a:has(span.sds-comps-text)')
        for anchor in news_anchors[:5]:
            title_tag = anchor.select_one('span.sds-comps-text')
            title = title_tag.get_text(strip=True) if title_tag else ''
            url = anchor.get('href', '').strip()
            if not title or not url or url in sent_urls: continue
            if any(word in title for word in exceptionalWords) or any(site in url for site in exceptionalSites): continue
            try:
                await bot.send_message(chat_id=CHAT_ID, text=f"[{company}]\n{title}\n{url}")
                save_sent_article(url, title)
                sent_urls.add(url)
                await asyncio.sleep(1)
            except: pass
    driver.quit()

if __name__ == "__main__":
    asyncio.run(news_release())
