import asyncio
import sys

import requests
from playwright.async_api import async_playwright

from cc import cc

# Configuration
GAME_PIN = "5721072"  # Replace with game pin
NUM_BOTS = 8  # Number of bots to spawn
HEADLESS = False  # Set to True to run without visible browser windows
BROWSER_TYPE = "chromium"  # Options: "chromium", "firefox", "webkit"
KAHOOT_URL = f"https://kahoot.it/?pin={GAME_PIN}"


def generate_nickname():
    """Generate a random human name for the bot nickname."""
    try:
        response = requests.get("https://api.jerryxf.net/generators/human_name", timeout=5)
        response_json = response.json()
        name = response_json["data"]
        truncated_name = name[:14]  # Truncate if exceeds 14 characters
        return truncated_name
    except Exception as e:
        print(cc("RED", f"Error generating nickname: {e}"))
        # Fallback to a simple generated name
        import random
        return f"Bot{random.randint(1000, 9999)}"


async def join_kahoot(context_id: int, browser, game_pin: str):
    """
    Join a Kahoot game using an isolated browser context.
    Each context has its own cookies/storage, bypassing Kahoot's tab detection.
    """
    # Create a new isolated browser context
    context = await browser.new_context()
    page = await context.new_page()

    nickname = generate_nickname()
    print(cc("CYAN", f"[Bot {context_id}] Starting with nickname: {nickname}"))

    try:
        # Navigate to Kahoot with the game pin
        print(cc("GREEN", f"[Bot {context_id}] Navigating to Kahoot..."))
        await page.goto(KAHOOT_URL, timeout=30000)

        # Wait for the nickname input to appear and fill it
        print(cc("YELLOW", f"[Bot {context_id}] Waiting for nickname input..."))
        # Try multiple possible selectors
        nickname_input = page.locator(
            'input[data-functional-selector="nickname-input"], '
            'input[name="nickname"], '
            'input[placeholder*="nickname" i]'
        ).first
        await nickname_input.wait_for(state="visible", timeout=20000)
        await nickname_input.fill(nickname)

        # await page.wait_for_timeout(50)

        # Click the join button
        print(cc("GREEN", f"[Bot {context_id}] Joining game..."))
        join_button = page.locator(
            'button[data-functional-selector="nickname-button"], '
            'button[type="submit"], '
            'button:has-text("OK"), '
            'button:has-text("Join")'
        ).first
        await join_button.click()

        # Wait for successful join confirmation
        await page.wait_for_timeout(1000)
        print(cc("BLUE", f"[Bot {context_id}] ✓ Joined as '{nickname}'"))

        # Keep the context alive - return it so we can manage it later
        return {"context": context, "page": page, "nickname": nickname, "id": context_id}

    except Exception as e:
        print(cc("RED", f"[Bot {context_id}] Error: {e}"))
        await context.close()
        return None


async def answer_question(bot_session, answer_index: int):
    """
    Click an answer button for a bot.
    answer_index: 0=top-left, 1=top-right, 2=bottom-left, 3=bottom-right
    For true/false: 0=left(true), 1=right(false)
    """
    page = bot_session["page"]
    bot_id = bot_session["id"]

    try:
        # Kahoot answer buttons have data-functional-selector attributes
        # For 4-answer questions: answer-0, answer-1, answer-2, answer-3
        # For 2-answer questions (true/false): answer-0, answer-1
        answer_button = page.locator(f'[data-functional-selector="answer-{answer_index}"]')

        # Check if button exists and is visible
        if await answer_button.count() > 0:
            await answer_button.click()
            print(cc("GREEN", f"[Bot {bot_id}] Clicked answer {answer_index}"))
        else:
            print(cc("YELLOW", f"[Bot {bot_id}] Answer button {answer_index} not found"))

    except Exception as e:
        print(cc("RED", f"[Bot {bot_id}] Error clicking answer: {e}"))


async def answer_all_bots(bot_sessions, answer_index: int):
    """Send the same answer to all bots simultaneously."""
    tasks = [answer_question(bot, answer_index) for bot in bot_sessions if bot is not None]
    await asyncio.gather(*tasks)


async def auto_random_answer(bot_session):
    """Continuously monitor for questions and answer randomly (optional feature)."""
    page = bot_session["page"]
    bot_id = bot_session["id"]

    import random

    try:
        while True:
            # Wait for answer buttons to appear
            answer_buttons = page.locator('[data-functional-selector^="answer-"]')

            # Check if any answer buttons are visible
            if await answer_buttons.count() > 0:
                # Get number of available answers
                num_answers = await answer_buttons.count()
                random_index = random.randint(0, num_answers - 1)

                await answer_question(bot_session, random_index)

                # Wait a bit before checking for next question
                await page.wait_for_timeout(2000)
            else:
                # No questions yet, wait a bit
                await page.wait_for_timeout(500)

    except Exception as e:
        print(cc("RED", f"[Bot {bot_id}] Auto-answer stopped: {e}"))


async def main():
    # Check for command-line arguments for browser type
    browser_type = BROWSER_TYPE
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["chromium", "firefox", "webkit"]:
            browser_type = arg

    print(cc("CYAN", "=" * 50))
    print(cc("CYAN", "       Kahoot Bot - Playwright Edition"))
    print(cc("CYAN", "=" * 50))
    print(cc("GRAY", f"Game PIN: {GAME_PIN}"))
    print(cc("GRAY", f"Number of bots: {NUM_BOTS}"))
    print(cc("GRAY", f"Browser: {browser_type.upper()}"))
    print(cc("GRAY", f"Headless mode: {HEADLESS}"))
    print(cc("CYAN", "=" * 50))

    async with async_playwright() as p:
        # Select browser based on configuration
        if browser_type.lower() == "firefox":
            browser_launcher = p.firefox
        elif browser_type.lower() == "webkit":
            browser_launcher = p.webkit
        else:
            browser_launcher = p.chromium

        # Launch browser instance
        print(cc("GREEN", f"Launching {browser_type} browser..."))
        browser = await browser_launcher.launch(headless=HEADLESS)

        # Spawn all bots concurrently
        print(cc("GREEN", f"Spawning {NUM_BOTS} bots..."))
        tasks = [join_kahoot(i + 1, browser, GAME_PIN) for i in range(NUM_BOTS)]
        bot_sessions = await asyncio.gather(*tasks)

        # Filter out failed sessions
        active_bots = [bot for bot in bot_sessions if bot is not None]
        print(cc("CYAN", f"\n✓ {len(active_bots)}/{NUM_BOTS} bots joined successfully!"))

        if not active_bots:
            print(cc("RED", "No bots were able to join. Exiting..."))
            await browser.close()
            return

        # Interactive answer control
        print(cc("CYAN", "\n" + "=" * 50))
        print(cc("CYAN", "       Answer Control"))
        print(cc("CYAN", "=" * 50))
        print(cc("GRAY", "Commands:"))
        print(cc("GRAY", "  1 - Click top-left (Red/Triangle)"))
        print(cc("GRAY", "  2 - Click top-right (Blue/Diamond)"))
        print(cc("GRAY", "  3 - Click bottom-left (Yellow/Circle)"))
        print(cc("GRAY", "  4 - Click bottom-right (Green/Square)"))
        print(cc("GRAY", "  r - Send random answer to all bots"))
        print(cc("GRAY", "  a - Enable auto-random answers"))
        print(cc("GRAY", "  q - Quit and close all bots"))
        print(cc("CYAN", "=" * 50))

        auto_mode = False
        auto_tasks = []

        # Input loop
        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, cc("YELLOW", "\nEnter command: ")
                )
                user_input = user_input.strip().lower()

                if user_input == "q":
                    print(cc("RED", "Quitting..."))
                    break
                elif user_input == "r":
                    import random
                    random_answer = random.randint(0, 3)
                    print(cc("GREEN", f"Sending random answer {random_answer} to all bots..."))
                    await answer_all_bots(active_bots, random_answer)
                elif user_input == "a":
                    if not auto_mode:
                        print(cc("GREEN", "Enabling auto-random answers for all bots..."))
                        auto_tasks = [asyncio.create_task(auto_random_answer(bot)) for bot in active_bots]
                        auto_mode = True
                    else:
                        print(cc("YELLOW", "Auto mode already enabled"))
                elif user_input in ["1", "2", "3", "4"]:
                    answer_index = int(user_input) - 1
                    print(cc("GREEN", f"Sending answer {answer_index} to all bots..."))
                    await answer_all_bots(active_bots, answer_index)
                else:
                    print(cc("RED", "Invalid command. Use 1-4, r, a, or q."))

            except (EOFError, KeyboardInterrupt):
                break

        # Cancel auto-answer tasks if running
        if auto_tasks:
            for task in auto_tasks:
                task.cancel()

        # Cleanup: close all contexts
        print(cc("YELLOW", "Closing all bot sessions..."))
        for bot in active_bots:
            await bot["context"].close()

        await browser.close()
        print(cc("GREEN", "Done!"))


if __name__ == "__main__":
    asyncio.run(main())
