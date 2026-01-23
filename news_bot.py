import asyncio
import os
import csv
import time
import telegram
from google import genai # 최신 라이브러리로 변경
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ✅ 설정값
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Gemini 최신 설정 방식 (2026 기준)
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

bot = telegram.Bot(token=TELEGRAM_TOKEN)
csv_file = 'sent_news.csv'

# ✅ 본문 추출 함수 (기존과 동일)
def get_article_content(driver, url):
    try:
        driver.get(url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        paragraphs = soup.find_all(['p', 'div'], class_=['article_body', 'art_body', 'news_con', 'article_view'])
        if not paragraphs: paragraphs = soup.find_all('p')
        content = " ".join([p.get_text(strip=True) for p in paragraphs])
        return content[:2000]
    except:
        return ""

# ✅ AI 요약 함수 (최신 라이브러리 버전)
async def get_summary(title, content):
    if not client: return "API 키 설정 필요"
    if len(content) < 100: return "본문 내용 부족으로 요약 불가"
    
    try:
        prompt = f"다음 뉴스 기사를 3줄 요약해줘.\n제목: {title}\n본문: {content}"
        # 최신 모델 gemini-2.0-flash 사용
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f"요약 에러: {e}")
        return "요약 생성 실패"

# ✅ [중요] IndexError 방지 로직이 추가된 함수
def load_sent_articles():
    if not os.path.exists(csv_file): return set()
    sent_set = set()
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            if row: # 줄에 내용이 있을 때만 읽음 (IndexError 방지)
                sent_set.add(row[0])
    return sent_set

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
    companies = ["더즌", "dozn", "카카오뱅크", "카카오페이", "오픈에셋", "스위치원"]

    for company in companies:
        search_url = f'https://search.naver.com/search.naver?where=news&query="{company}"&sm=tab_opt&sort=1'
        driver.get(search_url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        for item in soup.select('a.news_tit')[:2]:
            title = item.get_text(strip=True)
            url = item.get('href', '').strip()

            if not title or not url or url in sent_urls: continue
            
            content = get_article_content(driver, url)
            summary = await get_summary(title, content)
            
            message = f"📢 [{company}]\n📌 {title}\n\n🤖 AI 요약:\n{summary}\n\n🔗 {url}"
            
            try:
                await bot.send_message(chat_id=CHAT_ID, text=message)
                save_sent_article(url, title)
                sent_urls.add(url)
                await asyncio.sleep(2)
            except: pass

    driver.quit()

if __name__ == "__main__":
    asyncio.run(news_release())
