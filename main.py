from turtle import st
from playwright.async_api import async_playwright, BrowserContext
from core import get_answers, get_questions
from login import log_in, is_logged_in
from db_manager import *
import asyncio
import hashlib

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


async def process_url(context: BrowserContext, url: str, sem: asyncio.Semaphore, db: DbManager):
    async with sem:
        page = await context.new_page()
        try:
            questions = await get_questions(context, url, page)

            for q_text, q_url in questions:
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
                    {"text": q_text, "question_url": q_url},
                    answer_data
                )
            print(f'done with url: {url}')
        except Exception as e:
            print(f"An error occurred while processing {url}: {e}")
        finally:
            await page.close()

async def main():
    await init_db()
    db = DbManager()
    
    sem = asyncio.Semaphore(3)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state='state.json')
        if not await is_logged_in(context):
            await log_in(context)

        for i in range(REPEAT):

            tasks = [process_url(context, url, sem, db) for url in topics_urls]
            await asyncio.gather(*tasks)

        await browser.close()
        await db.close()

if __name__ == '__main__':
    asyncio.run(main())

    

    