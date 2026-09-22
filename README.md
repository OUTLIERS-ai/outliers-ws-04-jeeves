# Jeeves: a personal-assistant cockpit over your own second brain and CRM

```
git clone https://github.com/OUTLIERS-ai/outliers-ws-04-jeeves && cd outliers-ws-04-jeeves && python install.py && python start.py
```

One browser page on your own computer. Every ability is a panel you can drag,
dock, stack as tabs, close, bring back and pop out onto another screen:

| Panel | What it shows |
|---|---|
| Chat | Your own Claude Code, working in your second brain with your CRM added. Replies stream in word by word. Model picker: best, deep, fast. |
| Today | Your CRM's `Today.md` (made by CRM Layer 7) and your second brain's day: today's daily note if you keep one, notes that moved in the last 3 days, unticked boxes. |
| Across everything | One screen that sums up what is moving: people to speak to, decisions waiting, notes moved, Claude use today, your other apps. |
| Recommendations | A markdown file in your second brain (`Inbox/Recommendations.md` by default) that you and your agents write to. |
| Vaults | Both vaults, read-only. Filter, search both, click `[[links]]`. |
| Agents | Every agent in `~/.claude/agents` and in each vault's `.claude/agents`, with its description and an "Ask in chat" button. |
| Activity | Your recent Claude Code conversations: which folder, how many turns, how many tokens. |
| Tokens | Today's tokens from Claude Code's own log files, by kind and by model; your 5-hour window if the free `ccusage` tool is installed. |
| Work board | ProjectForge (piece 3) inside the panel, if it is running. If not, the link to install it. |
| FleetView | FleetView (piece 2), the same way. |

The animated orb at the top left, and above the chat, shows what Jeeves is
doing: slow when idle, pulsing while Claude thinks, bright while the answer
streams in.

## What it needs

- Python 3.8 or newer. Nothing to pip install: the server is Python's own library.
- Claude Code, installed and logged in (`claude` works in a terminal).
- Your second brain (from the second-brain series). Your CRM is optional.

## Install

```
python install.py
```

It asks 4 questions (second brain folder, CRM folder, agents folder, port),
offering what it finds, and writes `config.json`. Run it again and nothing
changes unless you give a different answer. It asks whether to start Jeeves
hidden when you log in; the answer defaults to no.

## Start and stop

```
python start.py            # opens http://127.0.0.1:4040/
python start.py --stop
```

On Windows the installer also makes `Start Jeeves (hidden).vbs`: double-click
it to start Jeeves with no window at all.

## What it will not do

- It never listens on your network: 127.0.0.1 only.
- It never writes to your vaults. The vault panels only read.
- It never runs Claude on a timer. Claude runs when you press Send, and at no other time.
- By default Claude may read but not change files (`"permission_mode": "dontAsk"`).
  Change that in `config.json` when you decide to (`"acceptEdits"` lets it edit notes).

## Tests

```
python -m pytest -q
```

They run against made-up vaults in a temporary folder, with a stand-in for
Claude Code (`tools/fake_claude.py`), so no test touches your real files or
spends a token.

## Try it on made-up data first

```
python tools/demo.py ../jeeves-demo --serve --port 4099
```

Then open http://127.0.0.1:4099/ . It builds "Sam the bookkeeper": 2 vaults,
3 agents and a day of fake Claude logs. The chat answers from a script.

## Uninstall

```
python install.py --uninstall
```

Removes the logon launcher if one was made and stops Jeeves. Then delete this folder.

The full guide, with pictures and the story of how the original was built, is
in `guide/GUIDE.md`.
