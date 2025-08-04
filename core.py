from bs4 import BeautifulSoup
from playwright.async_api import  BrowserContext, TimeoutError
from login import is_logged_in, log_in
import asyncio
import re


async def get_questions(context: BrowserContext, url: str, page=None):
    if page is None or page.is_closed():
        page = await context.new_page()
    await page.goto(url, wait_until='load', timeout=60000)
    while True:
        try:
            async with page.expect_response(lambda res: "https://www.quora.com/graphql/gql_para_POST?q=MultifeedQuery" in res.url and res.status == 200, timeout=10000):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(5)
        except TimeoutError as e:
            break
    html = await page.content()
    await page.close()

    soup = BeautifulSoup(html, "html.parser")
    questions = soup.find_all("span", class_="c1tjc3o4")
    result = [(question.get_text(strip=True), question.a.get('href')) for question in questions if question != None]
    return result

async def get_answers(context: BrowserContext, url: str, page=None):

    if page is None or page.is_closed():
        page = await context.new_page()
    await page.goto(url=url, wait_until='load', timeout=60000)
    try:
        try:
            no_answer = page.locator(
                        'div.q-box.qu-borderAll'
                        ).filter(
                        has_text=re.compile(r"This question does not have any answers yet", re.IGNORECASE)
                        )
            if await no_answer.count() > 0:
                return []
        except TimeoutError:
            pass
        try:    
            await page.click('button:has-text("All related")', timeout=7000)
        except TimeoutError:
            print(f'couldnt click "All related" in url {url}')
            return []
        await asyncio.sleep(0.1)
        try:
            await page.locator("div.q-click-wrapper", has_text=re.compile(r"^Answers?\s*\(\d+\)$")).click()
        except TimeoutError:
            print(f'couldnt click Answers in url {url}')
            return []
        await asyncio.sleep(2)

        while True:
            more_links = page.locator('span.qt_read_more')
            count = await more_links.count()

            if count == 0:
                break

            try:
                await more_links.first.scroll_into_view_if_needed()
                await more_links.first.click()
                await asyncio.sleep(1)
            except (TimeoutError, Exception):
                break
        html = await page.content()
        await page.close()
        
        soup = BeautifulSoup(html, 'html.parser')
        answers = soup.find_all("div", class_=re.compile(r"q-box dom_annotate_question_answer_item_\d+"))
        result = []
        for answer in answers:
            if answer is None:
                continue
            try:
                text = answer.find('span', class_="q-box qu-userSelect--text").get_text(strip=True)
                author = answer.find('div', class_="q-box qu-display--inline")
                author_name = author.get_text()
                author_url = author.a.get('href')
                result.append((text, author_name, author_url))
            except Exception:
                continue
        return result
    finally:
        await page.close()