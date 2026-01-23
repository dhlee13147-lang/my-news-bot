import asyncio
import os
import csv
import time
import telegram
from google import genai
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
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
bot = telegram.Bot(token=TELEGRAM_TOKEN)
csv_file = 'sent_news.csv'

# 원본 리스트 고정
companies = ["더즌", "dozn", "카카오뱅크", "카카오페이", "오픈에셋", "스위치원"]
exceptionalWords = ['랭키파이', '보호자', '브랜드평판', '브랜드 평판', '트렌드지수', '트렌드 지수', '링크드인']

def load_sent_articles():
    if not os.path.exists(csv_file): return set()
    sent_set = set()
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            if row: sent_set.add(row[0])
    return sent_set

def save_sent_article(url, title):
    with open(csv_file, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([url, title])

def get_article_content(driver, url):
    try:
        driver.get(url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        paragraphs = soup.find_all(['p', 'div'], class_=['article_body', 'news_con', 'article_view'])
        if not paragraphs: paragraphs = soup.find_all('p')
        content = " ".join([p.get_text(strip=True) for p in paragraphs])
        return content[:2500]
    except: return ""

async def get_summary(title, content):
    if not client: return "API 키 미설정"
    await asyncio.sleep(6) 
    try:
        prompt = f"다음 뉴스 기사 본문을 읽고 3줄 요약해줘.\n제목: {title}\n본문: {content}"
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text.strip()
    except Exception as e:
        log(f"⚠️ 요약 오류: {e}")
        return "요약 생성 실패"

def create_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

async def news_release():
    log("🚀 뉴스 봇 작동 시작 (구조 기반 정밀 검색)")
    sent_urls = load_sent_articles()
    driver = create_driver()

    for company in companies:
        log(f"🔍 검색 키워드: {company}")
        search_url = f'https://search.naver.com/search.naver?where=news&query="{company}"&sm=tab_opt&sort=1'
        driver.get(search_url)
        time.sleep(3) 

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # ✅ [핵심 변경] data-heatmap-target이 ".tit"인 <a> 태그만 정확히 타격
        # 그리고 그 안에 span.sds-comps-text가 있는 경우만 긁어옵니다.
        news_anchors = soup.select('a[data-heatmap-target=".tit"]:has(span.sds-comps-text)')
        log(f"📈 정밀 검색된 뉴스 개수: {len(news_anchors)}")

        for anchor in news_anchors[:2]:
            title_tag = anchor.select_one('span.sds-comps-text')
            title = title_tag.get_text(strip=True) if title_tag else ''
            url = anchor.get('href', '').strip()

            if not title or not url or url in sent_urls: continue
            if any(word in title for word in exceptionalWords): continue

            log(f"✨ 새 뉴스 발견: {title}")
            content = get_article_content(driver, url)
            summary = await get_summary(title, content)
            
            message = f"📢 [{company}]\n📌 {title}\n\n🤖 AI 요약:\n{summary}\n\n🔗 {url}"
            try:
                await bot.send_message(chat_id=CHAT_ID, text=message)
                save_sent_article(url, title)
                sent_urls.add(url)
                log("✅ 전송 완료")
            except Exception as e:
                log(f"❌ 전송 실패: {e}")

    driver.quit()
    log("🏁 모든 작업 완료")

if __name__ == "__main__":
    asyncio.run(news_release())
