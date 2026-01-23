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

# ✅ 설정값
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Gemini 설정
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

bot = telegram.Bot(token=TELEGRAM_TOKEN)
csv_file = 'sent_news.csv'

# ✅ 기사 본문을 추출하는 함수
def get_article_content(driver, url):
    try:
        driver.get(url)
        time.sleep(2) # 페이지 로딩 대기
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 일반적인 뉴스 사이트의 본문 태그들을 찾아 텍스트 추출
        # 기사 본문은 보통 <article>이나 특정 클래스의 <div>에 들어있습니다.
        paragraphs = soup.find_all(['p', 'div'], class_=['article_body', 'art_body', 'news_con', 'article_view'])
        
        if not paragraphs:
            # 특정 클래스가 없을 경우 모든 p 태그 수집
            paragraphs = soup.find_all('p')
            
        content = " ".join([p.get_text(strip=True) for p in paragraphs])
        return content[:2000] # 너무 길면 AI가 힘들어하므로 앞부분 2000자만 사용
    except Exception as e:
        print(f"본문 추출 중 에러: {url} - {e}")
        return ""

# ✅ 본문을 기반으로 요약하는 함수
async def get_summary(title, content):
    if not model:
        return "Gemini API 키가 설정되지 않았습니다."
    if len(content) < 100:
        return "본문 내용이 너무 적어 요약할 수 없습니다."
    
    try:
        prompt = f"""
        너는 뉴스 요약 전문가야. 아래 뉴스 기사의 [본문]을 읽고 내용을 3줄로 요약해줘.
        형식은 '- '로 시작하는 리스트 형태면 좋겠어.
        
        제목: {title}
        본문: {content}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"AI 요약 에러: {e}")
        return "현재 요약을 생성할 수 없습니다."

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
        
        # 최신 기사 최대 2개만 처리 (본문까지 읽어야 하므로 개수를 제한합니다)
        for item in soup.select('a.news_tit')[:2]:
            title = item.get_text(strip=True)
            url = item.get('href', '').strip()

            if not title or not url or url in sent_urls:
                continue
            
            print(f"📄 기사 분석 중: {title}")
            
            # 1. 기사 본문 가져오기
            content = get_article_content(driver, url)
            
            # 2. AI 요약 실행
            summary = await get_summary(title, content)
            
            message = f"📢 [{company} 뉴스]\n\n📌 제목: {title}\n\n🤖 AI 본문 요약:\n{summary}\n\n🔗 링크: {url}"
            
            try:
                await bot.send_message(chat_id=CHAT_ID, text=message)
                save_sent_article(url, title)
                sent_urls.add(url)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"전송 실패: {e}")

    driver.quit()

if __name__ == "__main__":
    asyncio.run(news_release())
