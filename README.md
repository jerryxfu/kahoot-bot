# Kahoot Bot

A Kahoot bot that can join games and answer questions at your command.

### Installation

If you wish to use a virtual environment, you can use the included scripts (optional):

**Windows (Command Prompt):**

1. `create_venv.bat` - Creates a virtual environment
2. `activate_venv.bat` - Activates the virtual environment

**Windows & macOS/Linux (PowerShell):**

1. `create_venv.ps1` - Creates a virtual environment
2. `activate_venv.ps1` - Activates the virtual environment (cross-platform compatible)

**Unix-like systems (macOS/Linux):**

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
playwright install
```

### Usage

1. Edit the configuration on line 11 in `bot.py`:

```python
GAME_PIN = "000000"  # Replace with your game pin
```

2. Run the bot:

```bash
python bot.py
```

3. Use the answer controls during the game:

| Key   | Action                                     |
|-------|--------------------------------------------|
| `1-6` | Select answer, left-right top-bottom order |
| `r`   | Send random answer to all bots             |
| `a`   | Toggle auto-random answers                 |
| `q`   | Quit and close all bots                    |