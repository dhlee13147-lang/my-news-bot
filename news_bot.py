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

# ✅ 로그 즉시 출력 함수
def log(message):
    print(message, flush=True)

# ✅ 설정값
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Gemini 최신 설정
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
bot = telegram.Bot(token=TELEGRAM_TOKEN)
csv_file = 'sent_news.csv'

# ✅ 지정하신 회사 리스트 고정
COMPANIES = ["더즌", "dozn", "카카오뱅크", "카카오페이", "오픈에셋", "스위치원"]

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
        paragraphs = soup.find_all(['p', 'div'], class_=['article_body', 'art_body', 'news_con', 'article_view'])
        if not paragraphs: paragraphs = soup.find_all('p')
        content = " ".join([p.get_text(strip=True) for p in paragraphs])
        return content[:2500]
    except:
        return ""

async def get_summary(title, content):
    if not client: return "AI 키 미설정"
    if len(content) < 100: return "본문 내용이 적어 요약이 어렵습니다."
    try:
        prompt = f"다음 뉴스 기사 본문을 읽고 3줄로 핵심 요약해줘.\n제목: {title}\n본문: {content}"
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text.strip()
    except Exception as e:
        log(f"요약 에러: {e}")
        return "요약 생성 실패"

async def news_release():
    log("🚀 뉴스 봇 작동 시작")
    sent_urls = load_sent_articles()
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    log("✅ 브라우저 실행 성공")

    for company in COMPANIES:
        log(f"🔍 {company} 검색 중...")
        driver.get(f"https://search.naver.com/search.naver?where=news&query={company}&sort=1")
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for item in soup.select('a.news_tit')[:2]:
            title = item.get_text(strip=True)
            url = item.get('href', '').strip()

            if url in sent_urls:
                log(f"⏭️ 중복 패스: {title}")
                continue
            
            log(f"✨ 새 뉴스 발견: {title}")
            content = get_article_content(driver, url)
            summary = await get_summary(title, content)
            
            message = f"📢 [{company} 뉴스]\n📌 {title}\n\n🤖 AI 본문 요약:\n{summary}\n\n🔗 {url}"
            try:
                await bot.send_message(chat_id=CHAT_ID, text=message)
                save_sent_article(url, title)
                sent_urls.add(url)
                log(f"📤 전송 완료")
            except Exception as e:
                log(f"❌ 전송 실패: {e}")

    driver.quit()
    log("🏁 모든 작업 완료")

if __name__ == "__main__":
    asyncio.run(news_release())
