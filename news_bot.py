import asyncio
import os
import csv
import time
import telegram
from datetime import datetime  # 날짜 처리를 위해 추가
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def log(message):
    print(message, flush=True)

# ✅ 설정값
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

bot = telegram.Bot(token=TELEGRAM_TOKEN)
csv_file = 'sent_news.csv'

companies = ["더즌", "dozn", "카카오페이", "오픈에셋", "스위치원"]
exceptionalWords = ['랭키파이', '보호자', '브랜드평판', '브랜드 평판', '트렌드지수', '트렌드 지수', '링크드인']

def load_sent_articles():
    if not os.path.exists(csv_file): return set()
    sent_set = set()
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            # 첫 번째 열(URL)을 기준으로 중복 체크
            if row: sent_set.add(row[0])
    return sent_set

# 검색 날짜(date_str) 인자를 추가하여 CSV에 저장
def save_sent_article(url, title, date_str):
    with open(csv_file, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([url, title, date_str])

def create_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

async def news_release():
    log("🚀 뉴스 봇 작동 시작 (요약 기능 비활성화)")
    sent_urls = load_sent_articles()
    driver = create_driver()
    
    # 작업 시점의 날짜 생성 (YYYY-MM-DD 형식)
    today_str = datetime.now().strftime('%Y-%m-%d')

    for company in companies:
        log(f"🔍 검색 키워드: {company}")
        search_url = f'https://search.naver.com/search.naver?where=news&query="{company}"&sm=tab_opt&sort=1&nso=so%3Add%2Cp%3A1d'
        driver.get(search_url)
        time.sleep(3) 

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        news_anchors = soup.select('a[data-heatmap-target=".tit"]:has(span.sds-comps-text)')
        log(f"📈 정밀 검색된 뉴스 개수: {len(news_anchors)}")

        for anchor in news_anchors[:10]:
            title_tag = anchor.select_one('span.sds-comps-text')
            title = title_tag.get_text(strip=True) if title_tag else ''
            url = anchor.get('href', '').strip()

            if not title or not url or url in sent_urls: continue
            if any(word in title for word in exceptionalWords): continue

            log(f"✨ 새 뉴스 발견: {title}")
            
            message = f"📢 [{company}]\n📌 {title}\n\n🔗 {url}"
            
            try:
                await bot.send_message(chat_id=CHAT_ID, text=message)
                # 저장 시 '오늘 날짜'를 세 번째 열에 추가
                save_sent_article(url, title, today_str)
                sent_urls.add(url)
                log("✅ 전송 완료")
            except Exception as e:
                log(f"❌ 전송 실패: {e}")

    driver.quit()
    log("🏁 모든 작업 완료")

if __name__ == "__main__":
    asyncio.run(news_release())
