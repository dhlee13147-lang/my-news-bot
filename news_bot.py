import asyncio
import os
import csv
import time
import telegram
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ✅ 설정값 (GitHub Secrets)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Gemini AI 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telegram.Bot(token=TELEGRAM_TOKEN)
csv_file = 'sent_news.csv'

# ✅ 뉴스 본문을 가져와서 요약하는 함수
async def get_summary(title, url):
    try:
        prompt = f"다음 뉴스 기사의 제목을 참고하여 내용을 2문장으로 아주 짧게 요약해줘. 제목: {title}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "요약을 가져오지 못했습니다."

# (나머지 로드/저장 함수는 기존과 동일)
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
    companies = ["더즌", "dozn", "카카오뱅크", "카카오페이", "오픈에셋", "스위치원"]

    for company in companies:
        search_url = f'https://search.naver.com/search.naver?where=news&query="{company}"&sm=tab_opt&sort=1'
        driver.get(search_url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        news_anchors = soup.select('a:has(span.sds-comps-text)')

        for anchor in news_anchors[:3]: # 너무 많이 보내면 AI 호출이 많아지므로 3개로 제한
            title_tag = anchor.select_one('span.sds-comps-text')
            title = title_tag.get_text(strip=True) if title_tag else ''
            url = anchor.get('href', '').strip()

            if not title or not url or url in sent_urls: continue
            
            # ✅ AI 요약 실행
            summary = await get_summary(title, url)
            
            message = f"📢 [{company} 뉴스]\n\n📌 제목: {title}\n\n🤖 AI 요약: {summary}\n\n🔗 링크: {url}"
            
            try:
                await bot.send_message(chat_id=CHAT_ID, text=message)
                save_sent_article(url, title)
                sent_urls.add(url)
                await asyncio.sleep(2)
            except: pass
    driver.quit()

if __name__ == "__main__":
    asyncio.run(news_release())
