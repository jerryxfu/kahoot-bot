import json

from cc import cc

# Shared state: network module stores game data that bot.py can read
game_data = {
    "game_api_id": None,
    "q1_answers": None,  # list of {answer, correct} from firstGameBlockData
}


def attach_network_debugging(page, bot_id: int, verbose=False):
    """Only attach to bot 1 to avoid duplicate output."""
    if bot_id != 1:
        return

    if verbose:
        page.on("request", lambda request: print(
            f"[Bot {bot_id}] >> {request.method} {request.url}"
        ))

    page.on("websocket", lambda ws: handle_websocket(ws, bot_id))


def handle_websocket(ws, bot_id: int):
    print(cc("GRAY", f"[Bot {bot_id}] 🌐 WebSocket opened"))
    ws.on("framereceived", lambda payload: process_ws_frame(payload, bot_id))
    ws.on("close", lambda _: print(cc("GRAY", f"[Bot {bot_id}] WebSocket closed")))


def process_ws_frame(payload, bot_id: int):
    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8", errors="ignore")
        except Exception:
            return

    try:
        data = json.loads(payload)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    handle_game_message(item, bot_id)
        elif isinstance(data, dict):
            handle_game_message(data, bot_id)
    except json.JSONDecodeError:
        pass


def handle_game_message(data: dict, bot_id: int):
    channel = data.get("channel", "")

    if channel.startswith("/meta/"):
        return
    if channel not in ("/service/player", "/service/controller", "/service/status"):
        return

    inner = data.get("data")
    if not isinstance(inner, dict):
        return

    content_raw = inner.get("content")
    if not content_raw or not isinstance(content_raw, str):
        return

    try:
        content = json.loads(content_raw)
    except json.JSONDecodeError:
        return

    msg_id = inner.get("id")

    # Extract gameApiId from lobby message (id=17)
    if "gameApiId" in content:
        game_data["game_api_id"] = content["gameApiId"]

    # Q1 preview (id=9): full question + answers + correct flags
    if "firstGameBlockData" in content:
        block = content["firstGameBlockData"]
        q = block.get("question", "")
        choices = block.get("choices", [])

        game_data["q1_answers"] = choices

        print(cc("CYAN", f"\n{'=' * 50}"))
        print(cc("CYAN", f"  Q1: {q}"))
        print(cc("CYAN", f"{'=' * 50}"))
        for i, c in enumerate(choices):
            marker = "✓" if c.get("correct") else " "
            print(cc("GREEN" if c.get("correct") else "GRAY",
                     f"  [{marker}] {i + 1}: {c.get('answer', '?')}"))
        print()

    # Get-ready (id=1): question metadata
    if "gameBlockIndex" in content and msg_id == 1:
        idx = content["gameBlockIndex"]
        total = content["totalGameBlockCount"]
        qtype = content.get("type", "?")
        num_choices = content.get("numberOfChoices", "?")
        print(cc("YELLOW", f"⏳ Question {idx + 1}/{total} ({qtype}, {num_choices} choices)"))

    # Answer result (id=8)
    if "correctChoices" in content:
        correct = content["correctChoices"]
        chose = content.get("choice")
        points = content.get("points", 0)
        total = content.get("totalScore", "?")
        is_correct = content.get("isCorrect", False)
        icon = "✅" if is_correct else "❌"
        print(cc("GREEN" if is_correct else "RED",
                 f"  {icon} Correct: {correct}, Chose: {chose}, "
                 f"+{points}pts (total: {total})"))

    # Game over (id=13)
    if msg_id == 13 and "quizTitle" in content:
        rank = content.get("rank", "?")
        total = content.get("totalScore", "?")
        title = content.get("quizTitle", "?")
        correct_count = content.get("correctCount", "?")
        incorrect_count = content.get("incorrectCount", "?")
        print(cc("CYAN", f"\n{'=' * 50}"))
        print(cc("CYAN", f"  [Bot {bot_id}] Game Over: {title}"))
        print(cc("CYAN", f"  Rank: {rank} | Score: {total} | "
                         f"Correct: {correct_count} | Wrong: {incorrect_count}"))
        print(cc("CYAN", f"{'=' * 50}\n"))
