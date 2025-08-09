from playwright.async_api import async_playwright, BrowserContext
from core import get_answers, get_questions
from login import log_in, is_logged_in
from db_manager import *
import asyncio
import hashlib
import schedule
from random import randrange
from time import sleep
from datetime import datetime

topics_urls = [
    'https://www.quora.com/topic/Deep-Learning/top_questions',
    'https://www.quora.com/topic/Machine-Learning/top_questions',
    'https://www.quora.com/topic/Artificial-Intelligence/top_questions',
    'https://www.quora.com/topic/Data-Science/top_questions',
    'https://www.quora.com/topic/Computer-Vision/top_questions',
    'https://www.quora.com/topic/Artificial-Neural-Networks/top_questions'
]

REPEAT = 1
CONCURRENCY_LIMIT = 3


async def process_url(context: BrowserContext, url: str, sem: asyncio.Semaphore):
    async with sem:
        await init_db()
        db = DbManager()
        await db.init_hashes()
        page = await context.new_page()
        try:
            questions = await get_questions(context, url, page)


            for q_text, q_url in questions:
                q_hash = hashlib.sha256(q_url.encode()).hexdigest()
                if q_hash in db.question_hashes:
                    continue
                answers = await get_answers(context, q_url, page)
                if not answers:
                    continue
                answer_data = []
                for a_text,a_name, a_url in answers:
                    answer_data.append({
                        "text": a_text,
                        "author_name": a_name,
                        "author_url": a_url
                    })
                await db.add_question_with_answers(
                    {"text": q_text, "question_url": q_url, "hash": q_hash},
                    answer_data
                )
            print(f'done with url: {url}')
        except Exception as e:
            print(f"An error occurred while processing {url}: {e}")
        finally:
            await page.close()
            await db.close()

async def main():
    sem = asyncio.Semaphore(3)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state='state.json')
        if not await is_logged_in(context):
            await log_in(context)

        for i in range(REPEAT):

            tasks = [process_url(context, url, sem) for url in topics_urls]
            await asyncio.gather(*tasks)

        await browser.close()

def job():    
    print(f"running at {datetime.now()}")
    asyncio.run(main())

def schedule_time(run_per_day=4, start_hour=9, end_hour=22):
    schedule.clear("random_runs")
    random_start_hour = randrange(start_hour, end_hour - 2 * run_per_day)
    random_hours = [random_start_hour + i for i in range(0, 2*run_per_day, 2)]
    random_minutes = [randrange(0, 60) for _ in range(run_per_day)]
    for i in range(run_per_day):
        run_time = f"{random_hours[i]:02d}:{random_minutes[i]:02d}"
        print(f"scheduled at {run_time}")
        schedule.every().day.at(run_time).do(job).tag("random_runs")

if __name__ == '__main__':
    schedule.every().minute.at(":00").do(schedule_time).tag("schedule_time")
    schedule_time()
    while True:
        schedule.run_pending()
        sleep(60)

    
