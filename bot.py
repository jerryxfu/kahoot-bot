import asyncio
import random
import re
import sys

import aiohttp
from playwright.async_api import async_playwright

from cc import cc
from network import attach_network_debugging, game_data

# Configuration
GAME_PIN = "9173894"

HEADLESS = True  # set false to see browser tabs (mostly for debugging)
BROWSER_TYPE = "webkit"  # "chromium" (recommended), "firefox", "webkit"
KAHOOT_URL = f"https://kahoot.it/?pin={GAME_PIN}"

# Reaction keys: z x c v b n mapped to the 6 reaction types
REACTION_KEYS = {"z": 0, "x": 1, "c": 2, "v": 3, "b": 4, "n": 5}
REACTION_NAMES = ["👍 ThumbsUp", "👏 Clap", "❤️ Heart", "😂 Haha", "🤔 Thinking", "😮 Wow"]

FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


async def generate_nickname():
    """Generate a random human name for the bot nickname."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.jerryxf.net/generators/human_name",
                                   timeout=aiohttp.ClientTimeout(total=5)) as response:
                response_json = await response.json()
                name = response_json["data"]
                return name[:14]  # Truncate if exceeds 14 characters
    except Exception as e:
        print(cc("RED", f"Error generating nickname: {e}"))
        # Fallback to a simple generated name
        return f"Bot{random.randint(1000, 9999)}"


def extract_quiz_uuid(text: str) -> str | None:
    """Extract a quiz UUID from raw UUID or full Kahoot URL."""
    text = text.strip()
    uuid_pattern = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
    match = uuid_pattern.search(text)
    return match.group(0) if match else None


async def try_fetch_quiz(quiz_uuid: str):
    """Fetch quiz content from the Kahoot REST API and store it for answer hints."""
    url = f"https://play.kahoot.it/rest/kahoots/{quiz_uuid}"

    async with aiohttp.ClientSession(headers=FETCH_HEADERS) as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    questions = data.get("questions", [])
                    if questions:
                        # Store for live answer hints
                        game_data["fetched_questions"] = questions

                        title = data.get("title", "?")
                        print(cc("GREEN", f"\n🎯 Fetched: {title} ({len(questions)} questions)"))
                        print(cc("CYAN", "=" * 50))
                        for qi, q in enumerate(questions):
                            qtype = q.get("type", "quiz")
                            if qtype == "content":
                                slide_title = q.get("title", q.get("description", "(slide)"))
                                print(cc("GRAY", f"  S{qi + 1}: {slide_title}"))
                                continue

                            qtext = q.get("question", q.get("title", "?"))
                            print(cc("CYAN", f"  Q{qi + 1}: {qtext}"))
                            for ci, c in enumerate(q.get("choices", [])):
                                answer_text = c.get("answer", c.get("answerText", "?"))
                                marker = "✓" if c.get("correct") else " "
                                print(cc("GREEN" if c.get("correct") else "GRAY",
                                         f"    [{marker}] {ci + 1}: {answer_text}"))
                        print(cc("CYAN", "=" * 50))
                        return questions
                    else:
                        print(cc("YELLOW", "Quiz fetched but no questions found"))
                        print(cc("GRAY", f"  Keys: {list(data.keys())[:10]}"))
                elif response.status == 404:
                    print(cc("RED", "  Quiz not found (404). Check the UUID."))
                elif response.status == 403:
                    print(cc("RED", "  Access denied (403). Quiz may be private."))
                else:
                    print(cc("GRAY", f"  {url} → {response.status}"))
        except Exception as e:
            print(cc("RED", f"  Fetch error: {e}"))

    return None


async def join_kahoot(context_id: int, browser, game_pin: str):
    """Join a Kahoot game using an isolated browser context."""
    context = await browser.new_context()
    page = await context.new_page()
    attach_network_debugging(page, context_id, verbose=False)

    nickname = await generate_nickname()
    print(cc("CYAN", f"[Bot {context_id}] Starting with nickname: {nickname}"))

    try:
        # Navigate to Kahoot with the game pin
        print(cc("GREEN", f"[Bot {context_id}] Navigating to Kahoot..."))
        await page.goto(KAHOOT_URL, timeout=15000)

        # Wait for the nickname input to appear and fill it
        print(cc("YELLOW", f"[Bot {context_id}] Waiting for nickname input..."))
        # Try multiple possible selectors
        nickname_input = page.locator(
            'input[data-functional-selector="nickname-input"], '
            'input[name="nickname"], '
            'input[placeholder*="nickname" i]'
        ).first
        await nickname_input.wait_for(state="visible", timeout=15000)
        await nickname_input.fill(nickname)

        await page.wait_for_timeout(150)

        # Click the join button
        print(cc("GREEN", f"[Bot {context_id}] Joining game..."))
        join_button = page.locator(
            'button[data-functional-selector="nickname-button"], '
            'button[type="submit"], '
            'button:has-text("OK"), '
            'button:has-text("Join")'
        ).first
        await join_button.click()

        await page.wait_for_timeout(150)
        print(cc("BLUE", f"[Bot {context_id}] ✓ Joined as '{nickname}'"))

        return {"context": context, "page": page, "nickname": nickname, "id": context_id}

    except Exception as e:
        print(cc("RED", f"[Bot {context_id}] Error: {e}"))
        await context.close()
        return None


async def join_kahoot_with_retry(context_id: int, browser, game_pin: str, retries: int = 1):
    """Attempt to join and retry once if the first attempt fails."""
    total_attempts = retries + 1

    for attempt in range(1, total_attempts + 1):
        session = await join_kahoot(context_id, browser, game_pin)
        if session is not None:
            return session

        if attempt <= retries:
            print(cc("YELLOW", f"[Bot {context_id}] Join failed. Retrying ({attempt}/{retries})..."))
            await asyncio.sleep(0.3)

    print(cc("RED", f"[Bot {context_id}] Failed to join after {total_attempts} attempts."))
    return None


async def answer_question(bot_session, answer_index: int):
    """Click an answer button for a bot."""
    page = bot_session["page"]
    bot_id = bot_session["id"]

    try:
        # Kahoot answer buttons have data-functional-selector attributes in the format "answer-0", "answer-1", etc.
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


async def send_reaction(bot_session, reaction_index: int):
    """Send a reaction by opening the reaction menu then clicking the nth reaction."""
    page = bot_session["page"]
    bot_id = bot_session["id"]

    try:
        # Step 1: Open the reaction menu
        prompt_button = page.locator('[data-functional-selector="reaction-prompt-button"]')
        if await prompt_button.count() == 0:
            print(cc("YELLOW", f"[Bot {bot_id}] Reaction button not available"))
            return

        await prompt_button.click()
        await page.wait_for_timeout(200)

        # Step 2: Click the nth reaction item
        reaction_items = page.locator('[data-functional-selector="slide-reactions-item"]')
        count = await reaction_items.count()

        if reaction_index < count:
            await reaction_items.nth(reaction_index).click()
            name = REACTION_NAMES[reaction_index] if reaction_index < len(REACTION_NAMES) else str(reaction_index)
            print(cc("BLUE", f"[Bot {bot_id}] Reacted {name}"))
        else:
            print(cc("YELLOW", f"[Bot {bot_id}] Reaction {reaction_index} not found ({count} available)"))
    except Exception as e:
        print(cc("RED", f"[Bot {bot_id}] Error sending reaction: {e}"))


async def react_all_bots(bot_sessions, reaction_index: int):
    """Send the same reaction from all bots simultaneously."""
    tasks = [send_reaction(bot, reaction_index) for bot in bot_sessions if bot is not None]
    await asyncio.gather(*tasks)


async def send_random_answer(bot_session):
    """Send a random answer by first checking available answer buttons."""
    page = bot_session["page"]
    bot_id = bot_session["id"]

    try:
        # Check how many answer buttons are actually available
        answer_buttons = page.locator('[data-functional-selector^="answer-"]')
        num_answers = await answer_buttons.count()

        if num_answers > 0:
            random_index = random.randint(0, num_answers - 1)
            await answer_question(bot_session, random_index)
        else:
            print(cc("YELLOW", f"[Bot {bot_id}] No answer buttons found"))
    except Exception as e:
        print(cc("RED", f"[Bot {bot_id}] Error sending random answer: {e}"))


async def auto_random_answer(bot_session):
    """Continuously monitor for questions and answer randomly."""
    page = bot_session["page"]
    bot_id = bot_session["id"]
    last_question_answered = False

    try:
        while True:
            # Wait for answer buttons to appear
            answer_buttons = page.locator('[data-functional-selector^="answer-"]')

            # Get number of available answers
            num_answers = await answer_buttons.count()

            # Check if any answer buttons are visible and valid
            if num_answers > 0:
                # Only answer if we haven't already answered this question
                if not last_question_answered:
                    # Wait a moment for buttons to be fully interactive
                    await page.wait_for_timeout(60)

                    # Re-check count to ensure stability
                    num_answers = await answer_buttons.count()
                    if num_answers > 0:
                        random_index = random.randint(0, num_answers - 1)
                        await answer_question(bot_session, random_index)
                        last_question_answered = True

                    # Wait a bit before checking for next question
                    await page.wait_for_timeout(2500)
                else:
                    # Already answered, wait for buttons to disappear before next question
                    await page.wait_for_timeout(500)
            else:
                # No questions yet, reset flag for next question
                last_question_answered = False
                await page.wait_for_timeout(60)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(cc("RED", f"[Bot {bot_id}] Auto-answer stopped: {e}"))


async def handle_u_command(user_input: str):
    """Handle the 'u' command: fetch quiz by UUID (inline arg or prompted)."""
    arg = user_input[1:].strip()

    if not arg:
        arg = await asyncio.get_running_loop().run_in_executor(
            None, input, cc("CYAN", "Paste quiz UUID or URL: ")
        )

    quiz_uuid = extract_quiz_uuid(arg)
    if quiz_uuid:
        print(cc("YELLOW", f"Fetching quiz {quiz_uuid}..."))
        await try_fetch_quiz(quiz_uuid)
    else:
        print(cc("RED", "No valid UUID found in input."))


async def main():
    browser_type = BROWSER_TYPE
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["chromium", "firefox", "webkit"]:
            browser_type = arg

    print(cc("CYAN", "=" * 50))
    print(cc("CYAN", "       Kahoot Bot"))
    print(cc("CYAN", "=" * 50))

    # Ask for number of bots
    while True:
        try:
            num_bots_input = input(cc("YELLOW", "Enter number of bots to spawn: "))
            num_bots = int(num_bots_input.strip())
            if num_bots > 0:
                break
            else:
                print(cc("RED", "Please enter a positive number."))
        except ValueError:
            print(cc("RED", "Invalid input. Please enter a number."))

    print(cc("GRAY", f"Game PIN: {GAME_PIN}"))
    print(cc("GRAY", f"Number of bots: {num_bots}"))
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
        print(cc("GREEN", f"Spawning {num_bots} bots..."))
        tasks = [join_kahoot_with_retry(i + 1, browser, GAME_PIN, retries=1) for i in range(num_bots)]
        bot_sessions = await asyncio.gather(*tasks)

        # Filter out failed sessions
        active_bots = [bot for bot in bot_sessions if bot is not None]
        print(cc("CYAN", f"\n✓ {len(active_bots)}/{num_bots} bots joined successfully!"))

        if not active_bots:
            print(cc("RED", "No bots were able to join. Exiting..."))
            await browser.close()
            return

        # Interactive answer control
        print(cc("CYAN", "\n" + "=" * 50))
        print(cc("CYAN", "       Answer Control"))
        print(cc("CYAN", "=" * 50))
        print(cc("GRAY", "Commands:"))
        print(cc("BLUE", "  1-6") + cc("GRAY", " > Select answer"))
        print(cc("BLUE", "  r") + cc("GRAY", " > Send random answer to all bots"))
        print(cc("BLUE", "  a") + cc("GRAY", " > Toggle auto-random answers"))
        print(cc("BLUE", "  z x c v b n") + cc("GRAY", " > React: 👍 👏 ❤️ 😂 🤔 😮"))
        print(cc("BLUE", "  u [uuid|url]") + cc("GRAY", " > Fetch quiz answers"))
        print(cc("BLUE", "  q") + cc("GRAY", " > Quit and close all bots"))
        print(cc("CYAN", "=" * 50))

        auto_mode = False
        auto_tasks = []

        # Input loop
        while True:
            try:
                user_input = await asyncio.get_running_loop().run_in_executor(
                    None, input, cc("YELLOW", "\nEnter command: ")
                )
                user_input = user_input.strip()
                cmd = user_input.lower()

                if cmd == "q":
                    print(cc("RED", "Quitting..."))
                    break
                elif cmd == "r":
                    print(cc("GREEN", "Sending random answers to all bots..."))
                    tasks = [send_random_answer(bot) for bot in active_bots if bot is not None]
                    await asyncio.gather(*tasks)
                elif cmd == "a":
                    if not auto_mode:
                        print(cc("GREEN", "Enabling auto-random answers for all bots..."))
                        auto_tasks = [asyncio.create_task(auto_random_answer(bot)) for bot in active_bots]
                        auto_mode = True
                    else:
                        print(cc("YELLOW", "Disabling auto-random answers..."))
                        for task in auto_tasks:
                            task.cancel()
                        auto_tasks = []
                        auto_mode = False
                elif cmd in ["1", "2", "3", "4", "5", "6"]:
                    answer_index = int(cmd) - 1
                    print(cc("GREEN", f"Sending answer #{answer_index + 1} to all bots..."))
                    await answer_all_bots(active_bots, answer_index)
                elif cmd in REACTION_KEYS:
                    reaction_index = REACTION_KEYS[cmd]
                    print(cc("BLUE", f"Sending reaction to all bots..."))
                    await react_all_bots(active_bots, reaction_index)
                elif cmd == "u" or cmd.startswith("u "):
                    await handle_u_command(user_input)
                else:
                    print(cc("RED", "Invalid command. Use 1-6, r, a, z-n, u, or q."))

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
