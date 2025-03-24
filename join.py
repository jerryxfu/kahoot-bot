import pyautogui
import requests
import time
from cc import cc

"""
Sequence (sets of two tabs to give time to load the page):
1. Open new tab (Ctrl + T)
2 Type the URL (https://kahoot.it/)
3. Press Enter

4. Open another tab (Ctrl + T)
5. Type the URL (https://kahoot.it/)
6. Press Enter

7. Go to the previous tab (Ctrl + Shift + Tab)
8. Press Tab twice
9. Type the game pin
10. Press Enter


11. Go to the next tab (Ctrl + Tab)
12. Press Tab twice
13. Type the game pin
14. Press Enter

15. Go to the previous tab (Ctrl + Shift + Tab)
16. Press Tab twice
17. Type a random nickname
18. Press Enter

19. Go to the next tab (Ctrl + Tab)
20. Press Tab twice
21. Type a random nickname
22. Press Enter
"""

GAME_PIN = "0000000"  # Replace with the game pin
KAHOOT_URL = "https://kahoot.it/?pin=" + GAME_PIN
NUM_ITER = 10  # Number of bots is two times the number of iterations because they join in pairs

# Increase this value (seconds) if the script is going too fast due to performance or network overhead.
pyautogui.PAUSE = 0.25  # Generally, 0.1 to 0.3 works


def generate_nickname():
    response = requests.get("https://api.jerryxf.net/generators/human_name")
    response_json = response.json()

    name = response_json["data"]
    truncated_name = name[:14]  # Truncate the name if it exceeds 14 characters
    print(cc("BLUE", "+ " + truncated_name))
    return truncated_name


def open_tab():
    print(cc("GREEN", "> opening tab"))
    pyautogui.shortcut("ctrl", "t")
    pyautogui.write(KAHOOT_URL)
    pyautogui.press("enter")


def focus_pin_enter():
    print(cc("YELLOW", "> focusing input box"))
    pyautogui.press("tab", presses=2)
    print(cc("GREEN", "> typing game pin"))
    pyautogui.write(GAME_PIN)
    pyautogui.press("enter")


def focus_nickname_enter():
    print(cc("YELLOW", "> focusing input box"))
    pyautogui.press("tab", presses=2)
    print(cc("GREEN", "> typing nickname"))
    pyautogui.write(generate_nickname())
    pyautogui.press("enter")


print(cc("CYAN", "Focus on the browser window, starting in 3 seconds..."))
pyautogui.sleep(3)

start_time = time.time()

for _ in range(NUM_ITER):
    open_tab()  # Open first tab
    open_tab()  # Open second tab

    # print(cc("FUCHSIA", "MOV <<"))
    # pyautogui.shortcut("ctrl", "shift", "tab")  # Go to first tab
    # focus_pin_enter()

    # print(cc("FUCHSIA", "MOV >>"))
    # pyautogui.shortcut("ctrl", "tab")  # Go to second tab
    # focus_pin_enter()

    print(cc("FUCHSIA", "MOV <<"))
    pyautogui.shortcut("ctrl", "shift", "tab")  # Go to first tab
    focus_nickname_enter()

    print(cc("FUCHSIA", "MOV >>"))
    pyautogui.shortcut("ctrl", "tab")  # Go to second tab
    focus_nickname_enter()

print(cc("CYAN", "Elapsed time: " + str(round(time.time() - start_time, 2)) + "s"))

print(cc("GREEN", "Done, returning to the first tab!"))
pyautogui.shortcut("ctrl", "tab")
