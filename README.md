# Kahoot Bot

A Kahoot bot that can join games and answer questions automatically.

### Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

### Usage

1. Edit the configuration in `bot.py`:

```python
GAME_PIN = "5721072"  # Replace with your game pin
NUM_BOTS = 4  # Number of bots to spawn
HEADLESS = False  # Set to True to run without visible browser
```

2. Run the bot:

```bash
python bot.py
```

3. Use the answer controls during the game:
    - `1` - Top-left (Red/Triangle)
    - `2` - Top-right (Blue/Diamond)
    - `3` - Bottom-left (Yellow/Circle)
    - `4` - Bottom-right (Green/Square)
    - `q` - Quit and close all bots
