from playwright.async_api import  TimeoutError, BrowserContext

EMAIL = 'example@gmail.com'
PASSWORD = 'password'

async def log_in(context: BrowserContext ,email=EMAIL, password=PASSWORD):
        
    try:
            page = await context.new_page()
            await page.goto("https://www.quora.com", wait_until='domcontentloaded')

            await page.fill("input[name='email']", EMAIL)
            await page.fill("input[name='password']", PASSWORD)
            await page.click("button[type='button']")
            await page.wait_for_selector('div[class="q-box"]', timeout=10000)

            await context.storage_state(path="state.json")
            return True
    except TimeoutError as e:
        print(f'log in failed: {e}')
        return False
    finally:
         await page.close()

async def is_logged_in(context: BrowserContext):
        page = await context.new_page()
        await page.goto('https://quora.com', wait_until='load', timeout=60000)
        try:
            await page.wait_for_selector('div[class="q-box"]', timeout=10000)
            await page.close()
            return True
        except TimeoutError:
            await page.close()
            return False
        finally:
            await page.close()
