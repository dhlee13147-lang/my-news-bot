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

# ✅ 원래 사용하시던 키워드 리스트
companies = ["더즌", "dozn", "카카오뱅크", "카카오페이", "오픈에셋", "스위치원"]
exceptionalWords = ['랭키파이', '보호자', '브랜드평판', '브랜드 평판', '트렌드지수', '트렌드 지수', '링크드인']
exceptionalSites = ['n.news.naver.com', 'www.pinpointnews.co.kr', 'www.pointdaily.co.kr', 'cwn.kr', 'www.stardailynews.co.kr', 'www.raonnews.com']

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

# ✅ 기사 본문을 가져오는 함수
def get_article_content(driver, url):
    try:
        driver.get(url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # 일반적인 뉴스 본문 영역 추출
        paragraphs = soup.find_all(['p', 'div'], class_=['article_body', 'news_con', 'article_view'])
        if not paragraphs: paragraphs = soup.find_all('p')
        content = " ".join([p.get_text(strip=True) for p in paragraphs])
        return content[:2000]
    except:
        return ""

# ✅ AI 요약 함수
async def get_summary(title, content):
    if not client: return "요약을 생성할 수 없습니다 (API 키 확인)."
    if len(content) < 100: return "본문 내용이 적어 요약이 어렵습니다."
    try:
        prompt = f"뉴스 기사 본문을 읽고 3줄로 요약해줘.\n제목: {title}\n본문: {content}"
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text.strip()
    except:
        return "요약 생성 중 오류가 발생했습니다."

def create_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

async def news_release():
    log("🚀 뉴스 봇 작동 시작")
    sent_urls = load_sent_articles()
    driver = create_driver()

    for company in companies:
        log(f"🔍 검색 키워드: {company}")
        # ✅ 원래 사용하시던 쿼리 방식 그대로 유지 (큰따옴표 포함)
        search_url = f'https://search.naver.com/search.naver?where=news&query="{company}"&sm=tab_opt&sort=1'
        driver.get(search_url)
        time.sleep(3) 

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # ✅ [복구] 원래 사용하시던 선택자 로직
        news_anchors = soup.select('a:has(span.sds-comps-text)')
        log(f"📈 발견된 뉴스 개수: {len(news_anchors)}")

        for anchor in news_anchors[:3]: # 최신 3개만 확인
            title_tag = anchor.select_one('span.sds-comps-text')
            title = title_tag.get_text(strip=True) if title_tag else ''
            url = anchor.get('href', '').strip()

            if not title or not url or url in sent_urls: continue
            if any(word in title for word in exceptionalWords): continue
            if any(site in url for site in exceptionalSites): continue

            log(f"✨ 새 뉴스 처리 중: {title}")
            
            # 본문 가져오기 및 요약
            content = get_article_content(driver, url)
            summary = await get_summary(title, content)
            
            message = f"📢 [{company}]\n📌 {title}\n\n🤖 AI 요약:\n{summary}\n\n🔗 {url}"
            
            try:
                await bot.send_message(chat_id=CHAT_ID, text=message)
                save_sent_article(url, title)
                sent_urls.add(url)
                log(f"✅ 전송 성공")
                await asyncio.sleep(2)
            except Exception as e:
                log(f"❌ 전송 실패: {e}")

    driver.quit()
    log("🏁 모든 작업 완료")

if __name__ == "__main__":
    asyncio.run(news_release())
