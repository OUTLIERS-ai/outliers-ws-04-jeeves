---
title: Jeeves — A Personal-Assistant Cockpit Over Your Own Second Brain
subtitle: Chat with your own Claude Code, see your day, your vaults, your agents and your token use, each in a panel you can move
repo: https://github.com/OUTLIERS-ai/outliers-ws-04-jeeves
piece: 4
---

## What it is

Jeeves is 1 page in your web browser, served by a small program on your own computer. The page is split into panels. Each panel does 1 job. You can drag a panel anywhere, stack panels as tabs, close a panel and bring it back, and pop any panel out into its own window so it can sit on a second screen.

![The whole cockpit on made-up data: Chat on the left, Today in the middle, a summary of everything on the right, tokens below it](img/cockpit-start.png)

The 10 panels:

| Panel | What you see |
|---|---|
| Chat | A conversation with your own Claude Code. It works inside your second-brain folder, with your CRM folder added, so it can read both. |
| Today | The ranked `Today.md` page your CRM builds (CRM Layer 7), plus your second brain's day: today's daily note if you keep one, notes that changed in the last 3 days, and boxes you left unticked. |
| Across everything | 1 screen that sums up what is moving: people to speak to, decisions waiting for you, notes that changed, Claude use today, and whether your other apps are running. |
| Recommendations | A markdown file in your second brain that you and your agents write suggestions into. |
| Vaults | Both vaults, read-only. Filter by name, search both, click a `[[link]]` to follow it. |
| Agents | Every Claude Code agent you have, with what each one is for, and an "Ask in chat" button. |
| Activity | Your recent Claude Code conversations: which folder, how many turns, how many tokens. |
| Tokens | Today's tokens, by kind and by model, read from Claude Code's own log files. |
| Work board | ProjectForge (piece 3) inside the panel, when it is running. |
| FleetView | FleetView (piece 2) inside the panel, when it is running. |

At the top left, and above the chat, is the orb: an animated circle of light and runes. It turns slowly when Jeeves is idle, pulses while Claude is thinking, and brightens while the answer is coming in.

## Why you would want it

Once you run agents, your work is spread across folders, terminals and apps. The CRM knows who to call. The second brain knows what you decided. Claude Code knows what it did today, and how many tokens it used doing it. None of them shows you the others.

Jeeves puts them on 1 screen and gives you 1 place to ask a question about any of them. The answer comes from your own Claude Code, so it already knows your rulebook, your agents and your skills. It costs nothing beyond your Claude subscription, and nothing leaves your computer except the messages Claude Code itself sends.

Ashley's ruling on what Jeeves is for, made on 2026-06-20: it is a full cockpit where every ability is a panel, not a chat box with an orb. "Jeeves is a FULL UI - that's the point."

## How we built it

Ashley built the original Jeeves for himself in June 2026. This section tells that build in order, from his build notes and records. The download you get is a clean rebuild of the parts that worked, for your setup rather than his.

### 2026-06-13: most of the system in 1 day

- **A web server on 127.0.0.1, port 4040**, written with Python's own library and nothing to install. 127.0.0.1 means "this computer only": nothing on your network can reach it. We kept this exactly.
- **The brain transplant.** The first version pinned a small model and did its own searching in Python, badly. It was replaced by a runner that drives the real Claude Code (`claude -p`) with every vault attached. We kept this idea: Jeeves has no brain of its own.
- **Permission tiers.** 3 levels: refuse, ask Ashley first, or allowed. Then control of the PC itself (screenshots, opening programs, typing), with clicks and keypresses needing approval.
- **Voice.** 5 speech engines were compared. The winner, Chatterbox (MIT licence), ran a cloned voice made from a well-known narrator's audiobook clips. It took 34 seconds to start and about 4 seconds per reply once warm. The clone was marked private-only, because the narrator has publicly objected to voice cloning.
- **The mic "not working"** turned out to be a silent virtual device set as the Windows default. Fixed with a picker that skips virtual devices.
- **Dockview panels**, a 3D map of agents, a live PowerShell terminal, a fast/deep model switch, email and calendar readers, a 45-minute watch pass, and the first Inbox panel.

### 2026-06-14 to 2026-06-17: additions

- **A heartbeat every 15 minutes** that researched new items before Ashley ruled on them.
- **Phone alerts** were built and switched off the same day, on Ashley's word.
- **A dead panel.** The Status panel looked for its box when the page loaded, before Dockview had built it, and stayed empty. The lesson: fill a panel when it mounts, never at page load. This rebuild does that for every panel.
- **Embedded apps.** ProjectForge and the outreach app were shown as real apps inside panels, and any panel could pop out into its own window for his 3 monitors.
- **"Jeeves suddenly dumb."** The default model had been switched to the smallest, fastest one. It fumbled tasks with several steps. Ruling: the strongest model by default. This rebuild's default is `best`.
- **Speed.** Keeping 1 Claude process running between messages cut the time to the first word from 3,704 ms to 1,381 ms.
- **The phone app** was installed on 2026-06-15. The login screen trapped the phone in a dead end, and Ashley ruled "get rid of all the auth": the private network became the only way in.
- **Telegram** as a way to reach Jeeves was removed on 2026-06-16. Jeeves replaced it.

### 2026-06-20: the redesign Ashley rejected

A new design went through research, a plan, a critique, a second plan, a second critique and a final plan. It proposed a "calm butler": 1 orb, 1 conversation, at most 4 cards, with the terminals and the agent map removed. Ashley's verdict: "it looks better but it uses most of the current usability", then "Jeeves is a FULL UI - that's the point". The plan was corrected to keep every panel and add a column that sums up what is moving across conversations, projects, outreach and agents. In this download that column is the **Across everything** panel.

### 2026-06-20 to 21, overnight: the orb

Ashley wanted Jeeves to look like a character from an anime. Claude guessed the look wrong twice. The fix was an original animated circle drawn in code (SVG, a way of drawing shapes in a web page), which reacts to the microphone and the voice, so no copyrighted picture ships with it. Its 2 rings of runes each spell out a line of text. This download uses the same code, cleaned, and the text is yours to set.

![The original orb, speaking, on 2026-06-21](img/original-orb-2026-06-21.png)

### 2026-06-21 to 2026-07-09: the new layout, then the pause

- **2026-06-21:** a 3-column layout went live as the default, with the old one kept at `/v1`.
- **2026-06-22:** a separate hands-free voice-control program was built and archived the same day. About half a second at best, plus the time for an AI answer, was not fast enough.
- **2026-07-01 to 02:** a code audit found that the login store failed open (let people in) if its file was damaged. It was fixed to lock instead. It also found that Jeeves started its own copy of the outreach app on a shared port, and the outreach app quietly reused that copy, so a fix to the outreach app looked dead.
- **2026-07-08:** the last heartbeat. Jeeves was paused for token burn. On the same date ProjectForge was stopped for using about 230 million input tokens in 30 days. The Jeeves heartbeat and watch pass each started a fresh Claude session on a timer, which is the same pattern. No separate token count for Jeeves was recorded.
- **2026-07-09:** the last attempt to start it failed, because a folder it needed (the voice code) was missing. The server would not run without files that lived outside its own folder.

### What this download keeps, and what it drops

| Kept | Dropped, and why |
|---|---|
| Local server on 127.0.0.1 | Timers of any kind: the token burn |
| Claude Code as the brain | The cloned voice: legal and reputational risk |
| Every ability as a Dockview panel, with pop-out | Login screen and phone app: loopback only, so neither is needed |
| The orb | PC control and the terminal: too much power for a first install |
| A summary of everything (the corrected redesign) | Starting other apps: the shared-port clash |
| The best model by default | Anything outside its own folder: the failed start on 2026-07-09 |

![Asking Jeeves a question. On made-up data, and with a stand-in for Claude, so the picture cost no tokens](img/cockpit-chat.png)

## Pros and cons

| | Pros | Cons |
|---|---|---|
| Cost | Nothing runs on a timer. Reading your vaults and logs costs 0 tokens. | Every chat message is a Claude Code run, and each run re-reads your rulebook and the conversation so far. We did not measure that figure for a member's setup. |
| Speed | The reading panels never start Claude, so they answer without an AI wait. | No Claude process is kept warm, so the first word takes longer than the original's 1,381 ms. |
| Brain | Your own Claude Code: every agent, skill and rulebook you have. | If Claude Code is not installed or not logged in, Chat cannot answer (every other panel still works). |
| Safety | 127.0.0.1 only; vault panels only read; by default Claude may read but not change files. | The default means Chat refuses when you ask it to edit a note, until you change the setting. |
| Breadth | 10 panels, all movable, layout saved. | It is a browser tab, not its own app window. |
| Install | Python's own library: nothing to pip install. | The 5-hour window figure needs `ccusage`, which needs Node.js. |

## Before you start

| You need | How to check |
|---|---|
| Python 3.8 or newer | In a terminal: `python --version` (on a Mac: `python3 --version`) |
| Claude Code, logged in | `claude --version` prints a number (2.1.278 on 2026-09-22), and typing `claude` opens it without asking you to log in |
| Git | `git --version` |
| Your second brain | The folder from the second-brain series. Its path, for example `C:\Users\<you>\Documents\Second Brain` |
| Your CRM (optional) | The folder from the CRM series. Without it, Today shows only your second brain |
| ccusage (optional) | `ccusage --version`. Needs Node.js; install with `npm install -g ccusage` (version 20.0.24 on 2026-09-22) |

## Install it

1. Open a terminal in the folder where you keep your downloads, then copy this link: https://github.com/OUTLIERS-ai/outliers-ws-04-jeeves
2. Clone it and go into it:

```
git clone https://github.com/OUTLIERS-ai/outliers-ws-04-jeeves
cd outliers-ws-04-jeeves
```

3. Run the installer:

```
python install.py
```

4. It checks Python and Claude Code first. If either is missing it says what to do and changes nothing.
5. It asks 4 questions. Press Enter to accept the answer in brackets, which is what it found:
   - where your second brain is (it reads the path your second-brain installer recorded)
   - where your CRM is (the same, from the CRM installer; leave it blank if you have none)
   - where your agents are (normally the `agents` folder inside `.claude` in your home folder)
   - which port to use: the number after the colon in the address, 4040 unless something else is using it
6. It asks whether to start Jeeves hidden every time you log in. The default is no. If you say yes on Windows, it puts a small file in your Startup folder that starts Jeeves with no window. On a Mac it writes a launch file and prints the 1 command that switches it on.
7. It writes `config.json` next to `install.py`. That is the only file it writes, apart from the launcher you chose. Run it again and it says "Nothing changed".
8. Start Jeeves:

```
python start.py
```

9. Your browser opens http://127.0.0.1:4040/ . There is no login. The first time you send a chat message, Claude Code starts up, which can take several seconds before the first word appears.

When it worked you see the orb top left, Chat on the left, Today in the middle and the summary on the right:

![What you should see the first time](img/cockpit-start.png)

> **Tip:** On Windows, the installer also makes `Start Jeeves (hidden).vbs` in the same folder. Double-click it to start Jeeves with no window. Stop it with `python start.py --stop`.

> **Warning:** Do not change `"permission_mode"` to `"bypassPermissions"` in config.json. That lets Claude do anything without asking, from a page that is always open.

## Using it day to day

**Start of the day.** Open Jeeves and read **Across everything**. It shows the top 4 people from your CRM's Today page, the top suggestions in your Recommendations file, how much changed in your second brain, and how much Claude has done today.

![Across everything: people, decisions, notes, Claude and apps on 1 screen](img/panel-overview.png)

**Today.** Your CRM's ranked page as it is, then your second brain. If you keep daily notes named by date (for example `Daily/2026-09-23.md`), today's note appears. If you do not, you still see what changed and what is left unticked. Build a fresh CRM page first with `python _engine/today.py --write` in your CRM folder.

![Today: the CRM page, then the day in the second brain](img/panel-today.png)

**Chat.** Type and press Enter. Shift+Enter makes a new line. The lines starting with an arrow show which files Claude is reading. **New conversation** starts afresh; otherwise Jeeves remembers the conversation, even after a restart. The model menu at the top chooses `best` (strongest), `deep` or `fast` (cheapest). What each maps to is in `config.json`.

**Vaults.** Pick Second brain or CRM, type to filter by name, or press Enter to search inside every note in both vaults.

![Vaults: a note from the made-up second brain, table and checkboxes included](img/panel-vaults.png)

**Agents.** Click a description to read it in full. **Ask in chat** starts a message with "Use the (name) agent to", so you only type what you want done.

![Agents from all 3 places they can live](img/panel-agents.png)

**Activity and Tokens.** Activity lists your Claude Code conversations from the last 7 days. Tokens shows today's total. Most tokens are "cache reads": Claude re-reading the conversation so far. They count towards your limits but are the cheapest kind.

![Activity: every Claude Code conversation, which folder, how many turns and tokens](img/panel-activity.png)

![Tokens: today, by kind and by model](img/panel-tokens.png)

**Recommendations.** Keep 1 file, `Inbox/Recommendations.md`, in your second brain. Ask your agents to add a line there instead of interrupting you. You decide in your own time.

![Recommendations: a file your agents write to](img/panel-inbox.png)

**Work board and FleetView.** If ProjectForge or FleetView is running, it appears inside the panel. If not, the panel says so and gives you the link.

![A work board that is not installed says so, with the link](img/panel-board.png)

**Moving panels.** Drag a tab by its title to another edge or into another group. The square button on each panel pops it into its own window. **+ Panel** brings back anything you closed. **Reset layout** puts everything back.

## Fit it to your own AI system

Each of these is a change you can ask your own Claude Code to make. Open a terminal in the `outliers-ws-04-jeeves` folder, type `claude`, and paste the prompt.

**1. A content-engine panel.** Shows the drafts in your content engine's latest wave.

```
Add a panel to Jeeves called "Drafts". Read-only. It lists the markdown files in the
newest folder under briefs/ in my content engine at <path to outliers-content-engine>,
from each wave's drafts/ folder, with the first line of each draft. Add the path to
config.json as "content_engine". Add a GET route in jeeves/server.py, a render function
in jeeves/static/app.js, and a test in tests/ against a made-up folder. Run the tests.
```

**2. A "who to call" panel with a button per person.**

```
Add a panel called "Who to call" that reads the table in my CRM's Today.md and shows
each person as a card. Each card gets a button "Draft a follow-up" that puts
"Use the follow-up-writer agent to draft a follow-up to <name>, using their CRM note"
into the chat box without sending it. Keep it read-only. Add a test.
```

**3. Your agents as buttons.** Turn the 3 agents you use most into 1-click buttons in the top bar.

```
In Jeeves, add a row of buttons to the top bar for the agents listed in a new
config.json key "agent_buttons" (a list of names). Each button fills the chat box with
"Use the <name> agent to " and focuses it. Nothing is sent until I press Enter.
```

**4. Saved layouts.** Morning, Deep work, Client prep.

```
Add 3 saved layouts to Jeeves: "Morning" (Across everything, Today, Chat),
"Deep work" (Chat and Vaults only) and "Client prep" (Today, Vaults, Chat).
Put them in a menu next to Reset layout. Use Dockview's toJSON/fromJSON.
```

**5. Let it edit notes, on your terms.** Change the permission mode, and tell Claude where it may write.

```
In config.json set "permission_mode" to "acceptEdits". Then add a rule to my second
brain's CLAUDE.md: "When working from Jeeves, only create or edit files in Inbox/ and
Daily/. Ask me before touching anything else."
```

**6. A voice panel.** Uses the voices already built into your browser, with no cloning.

```
Add a "Speak replies" switch to the Jeeves chat panel. When it is on, read each finished
reply aloud with the browser's built-in speechSynthesis, and set the orb to "speaking"
while it talks. Add a microphone button that uses the browser's speech recognition if
the browser has it, and hides itself if it does not.
```

**7. Recommendations written by your agents.** Give every agent 1 place to put suggestions.

```
In my second brain, add a rule to CLAUDE.md: "Any agent that has a suggestion for me
appends one line to Inbox/Recommendations.md in this form:
- [ ] **<the suggestion>** - <why, with a number> (from <agent name>, <date>)
It never acts on the suggestion itself."
```

**8. Only run when there is work.** If you ever add a scheduled job, make it check first.

```
I want a morning job that asks Jeeves's chat to summarise my day. Before it starts
Claude, it must check with plain Python whether anything changed since yesterday
(new lines in Today.md, new notes). If nothing changed, it exits without starting Claude.
Use a hidden .vbs launcher on Windows and pass CREATE_NO_WINDOW to every subprocess.
```

**9. Change the orb's words and the name.**

```
In config.json set "name" to "<your assistant's name>" and set "orb" inner and outer to
two short lines of my choosing. Restart Jeeves and check the runes changed.
```

## When it goes wrong

| What you see | Why | What to do |
|---|---|---|
| A panel is empty | The original's Status panel stayed empty because it was filled before it existed. This rebuild fills panels when they appear, so an empty panel now means the data is not there. | Press the refresh arrow on the panel. Read the message in it: it says which file it looked for. |
| Chat says Claude Code was not found | `claude` is not on your PATH, or Jeeves was started from a window that was open before you installed it. | Close every terminal, open a new one, check `claude --version`, then restart Jeeves. |
| Chat refuses to change a file | The default permission mode, `dontAsk`, lets Claude read but refuses anything that needs your approval. | See customisation 5. |
| Answers feel weak | The original hit this when its default was set to the smallest model. | Pick `best` in the model menu. |
| Work board or FleetView says "not running" | Jeeves only looks. It never starts another app, because the original starting its neighbour caused a clash on a shared port. | Start ProjectForge or FleetView yourself, then press the refresh arrow. |
| An embedded app is blank | An app loaded inside a hidden panel can paint blank. Jeeves waits until the panel is visible, but an app can also refuse to be shown inside another page. | Use the "open in its own tab" link in the panel's top line. |
| The work-board panel appeared blank for a moment | While building, our first screenshot caught it empty: each check for a stopped app could wait up to 0.8 seconds, 1 app after the other. | Fixed: both apps are asked at once, and the panel says "Checking" while it waits. |
| Token totals looked doubled | Claude Code writes the same reply more than once in its logs. | Fixed: each reply is counted once. If your numbers still differ from ccusage, ccusage is the reference. |
| "Could not listen on port 4040" | Something else is using the port. | `python start.py --port 4041`, or run `python install.py` again with another port. |
| It will not start at all | The original failed on 2026-07-09 because a folder it needed lived outside its own. This rebuild needs nothing outside its folder except your vaults. | Run `python install.py` again: it checks everything and says what is missing. |

> **Note:** Jeeves never writes to your vaults. If a note changed, something else changed it: Claude through Chat (only if you changed the permission mode), or one of your agents.

## Download

https://github.com/OUTLIERS-ai/outliers-ws-04-jeeves

```
git clone https://github.com/OUTLIERS-ai/outliers-ws-04-jeeves && cd outliers-ws-04-jeeves && python install.py && python start.py
```

![The orb, drawn in code: no image files](img/orb.png)
