# AI Project 3 - Generalized Tic Tac Toe

This repository contains two ways to use the project:

- local generalized Tic Tac Toe with a minimax agent
- live play against other teams through the AI P2P server API

The live workflow is the important part for competition use. This README is written as a practical runbook so you can start from zero and get to a running match quickly.

## Contents

- Prerequisites
- Project Structure
- First-Time Setup
- Local Play
- AI P2P Quick Start
- Team Setup
- Create and Manage Games
- View a Live Game
- Make Moves
- Recommended Match Workflow
- Useful Commands
- How the Server Behaves
- Troubleshooting
- Tests
- Algorithm Notes

## Prerequisites

- Python 3.10+
- PowerShell on Windows
- `curl` available in the shell

The remote client uses `curl` for network requests because the AI P2P server rejected direct Python HTTP calls in this environment while `curl` worked reliably.

## Project Structure

- `ttt/game.py`
  Core generalized Tic Tac Toe state and rules.
- `ttt/agent.py`
  Minimax agent with alpha-beta pruning.
- `ttt/cli.py`
  Local terminal gameplay.
- `ttt/ui.py`
  Local Tkinter UI.
- `ttt/p2p.py`
  AI P2P API client and remote-board parsing.
- `ttt/p2p_cli.py`
  Command-line interface for team/game management and live play.
- `tests/`
  Unit tests.
- `AI_P2P_API Document.pdf`
  Provided API documentation.

## First-Time Setup

Create and activate a virtual environment if you want an isolated Python setup:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

There are no extra required packages for the main project workflow beyond standard Python and `curl`.

## Local Play

Run a local human-vs-AI game:

```powershell
python -m ttt.cli --n 3 --m 3 --mode human-vs-ai --depth-x 4 --depth-o 4
```

Run local AI vs AI:

```powershell
python -m ttt.cli --n 5 --m 4 --mode ai-vs-ai --depth-x 3 --depth-o 3 --time-x 1.0 --time-o 1.0
```

Start with `O`:

```powershell
python -m ttt.cli --n 4 --m 3 --mode ai-vs-ai --first o
```

Run the Tkinter UI:

```powershell
python -m ttt.ui --n 3 --m 3 --mode human-vs-ai --depth-x 4 --depth-o 4
```

## AI P2P Quick Start

The AI P2P server uses one endpoint:

```text
https://www.notexponential.com/aip2pgaming/api/index.php
```

Authentication is done with headers:

- `userId`
- `x-api-key`

The easiest way to run the live CLI is with a local `.env` file.

This repo includes:

- `.env`
  Your local machine values. This file is ignored by git.
- `.env.example`
  A safe template you can copy for another machine.

Example `.env`:

```text
AIP2P_USER_ID=3733
AIP2P_API_KEY=YOUR_API_KEY
AIP2P_TEAM_ID=1484
AIP2P_OPPONENT_TEAM_ID=1492
AIP2P_GAME_ID=
AIP2P_BOARD_SIZE=5
AIP2P_TARGET=4
AIP2P_DEPTH=3
AIP2P_TIME_LIMIT=1.5
AIP2P_POLL_SECONDS=5
```

You can also set credentials in PowerShell instead:

```powershell
$env:AIP2P_USER_ID = "YOUR_USER_ID"
$env:AIP2P_API_KEY = "YOUR_API_KEY"
```

After that, you can omit `--user-id` and `--api-key` in the commands below.
If `AIP2P_TEAM_ID`, `AIP2P_OPPONENT_TEAM_ID`, or `AIP2P_GAME_ID` are set in `.env`,
you can omit those flags too.

Check that authentication works:

```powershell
python -m ttt.p2p_cli my-teams
python -m ttt.p2p_cli my-games
```

## Team Setup

### 1. See whether you already have a team

```powershell
python -m ttt.p2p_cli my-teams
```

### 2. Create a team if needed

```powershell
python -m ttt.p2p_cli create-team --name "Your Team Name"
```

Example output:

```text
Created team 1484
```

### 3. Add yourself to the team

New teams start empty. You must add yourself after creating the team.

```powershell
python -m ttt.p2p_cli add-member --team-id 1484 --member-user-id 3733
```

If `AIP2P_TEAM_ID` is already set in `.env`, you can shorten that to:

```powershell
python -m ttt.p2p_cli add-member --member-user-id 3733
```

### 4. Verify team members

```powershell
python -m ttt.p2p_cli team-members --team-id 1484
```

Expected shape:

```json
{
  "teamId": 1484,
  "userIds": [
    3733
  ]
}
```

### 5. Optional team maintenance

Remove a member:

```powershell
python -m ttt.p2p_cli remove-member --team-id 1484 --member-user-id 3733
```

## Create and Manage Games

### List your games

All games:

```powershell
python -m ttt.p2p_cli my-games
```

Only open games:

```powershell
python -m ttt.p2p_cli my-games --open-only
```

### Create a game against another team

Standard 3x3 Tic Tac Toe:

```powershell
python -m ttt.p2p_cli create-game --team-id 1484 --opponent-team-id 1453 --board-size 3 --target 3
```

Larger board example:

```powershell
python -m ttt.p2p_cli create-game --team-id 1484 --opponent-team-id 1453 --board-size 20 --target 10
```

If your `.env` already contains:

- `AIP2P_TEAM_ID`
- `AIP2P_OPPONENT_TEAM_ID`
- `AIP2P_BOARD_SIZE`
- `AIP2P_TARGET`

then you can simply run:

```powershell
python -m ttt.p2p_cli create-game
```

When `create-game` succeeds, the CLI automatically writes the returned game ID
into `AIP2P_GAME_ID` inside your local `.env` file.

Notes:

- `board-size` is the board width and height.
- `target` is how many in a row are needed to win.
- On a `3x3` board, the sensible target is `3`.
- The API is case-sensitive.

## View a Live Game

### Full game summary

```powershell
python -m ttt.p2p_cli game-details --game-id 5483
```

If `AIP2P_GAME_ID` is set in `.env`, you can shorten that to:

```powershell
python -m ttt.p2p_cli game-details
```

This shows:

- both teams
- board size and target
- move count
- current turn team
- inferred `X`/`O` symbols
- the board itself

### Board only

```powershell
python -m ttt.p2p_cli board --game-id 5483
```

### Recent moves

```powershell
python -m ttt.p2p_cli moves --game-id 5483 --count 10
```

Example output:

```text
moveId=124490 teamId=1484 symbol=O move=(1, 1)
```

## Make Moves

### Submit one move automatically

Use this when you want the agent to make exactly one move if it is your turn:

```powershell
python -m ttt.p2p_cli auto-move --game-id 5483 --team-id 1484 --depth 3 --time-limit 1.5
```

With `.env` defaults for game/team/depth/time limit, this can be as short as:

```powershell
python -m ttt.p2p_cli auto-move
```

What it does:

- downloads the current board
- reconstructs the game locally
- runs the minimax agent
- submits exactly one move if the turn belongs to your team

If it is not your turn, it will say so and do nothing.

### Keep polling and play automatically

Use this during a live match:

```powershell
python -m ttt.p2p_cli play-loop --game-id 5483 --team-id 1484 --depth 3 --time-limit 1.5 --poll-seconds 5
```

With `.env` defaults for game/team/depth/time/polling, this can be as short as:

```powershell
python -m ttt.p2p_cli play-loop
```

What it does:

- checks the game every few seconds
- prints updates when the board changes
- automatically submits a move when it becomes your turn

Stop it with `Ctrl+C`.

## Recommended Match Workflow

### First match setup

1. Fill in `.env` with `AIP2P_USER_ID`, `AIP2P_API_KEY`, and your team defaults.
2. Run `python -m ttt.p2p_cli my-teams`.
3. Create a team if needed.
4. Add yourself to the team.
5. Verify team membership.
6. Get the opponent team ID.
7. Update `AIP2P_OPPONENT_TEAM_ID` in `.env` if needed.
8. Create a game.
9. The CLI writes the returned game ID into `AIP2P_GAME_ID` in `.env`.
10. Check `game-details` once to confirm the game exists.
11. Start `play-loop` for that game.

### During the match

1. Keep `play-loop` running.
2. Use `game-details` or `board` in another terminal to inspect the current state.
3. If the opponent is inactive, the game will simply wait on their turn.

## Useful Commands

Show CLI help:

```powershell
python -m ttt.p2p_cli --help
```

Show help for a specific command:

```powershell
python -m ttt.p2p_cli create-game --help
python -m ttt.p2p_cli play-loop --help
```

## How the Server Behaves

These are the main things that can be confusing when you first test against other teams.

### The server is passive

The server does not make moves by itself.

It only stores game state and waits for whichever team owns the current turn to submit a move.

That means:

- if your team has moved, the opponent must move next
- if the opponent never sends a move, the game stays where it is
- running `game-details` only views the game, it does not play

### Games are turn-based

If it is not your turn, `auto-move` will not submit anything.

### Coordinates are zero-indexed

Moves are interpreted as `row,col`, starting from `0,0`.

### Teams must coordinate offline

You need to know the other team's `teamId` before you can challenge them.

## Troubleshooting

### `TEAM_ID` is not a number

If you run a command like:

```powershell
python -m ttt.p2p_cli team-members --team-id TEAM_ID
```

it will fail, because `TEAM_ID` is only a placeholder. Replace it with a real numeric value such as `1484`.

### `No team (or no members!) for team: ...`

This usually means the team exists but has no members yet.

Fix:

```powershell
python -m ttt.p2p_cli add-member --team-id 1484 --member-user-id 3733
```

### Opponent is not moving

This is usually not a bug. The opponent team simply has not submitted their move yet.

### `game-details` shows the board but no move happens

That is expected. `game-details` only reads the current server state.

Use:

- `auto-move` for one move
- `play-loop` for continuous play when it becomes your turn

### API key safety

Do not hardcode your API key into tracked source files. Prefer `.env` or environment variables:

```powershell
$env:AIP2P_USER_ID = "YOUR_USER_ID"
$env:AIP2P_API_KEY = "YOUR_API_KEY"
```

This repo ignores `.env`, so it is the preferred place for local secrets.

If your key was exposed in a shared place, regenerate it from the AI P2P website.

## Tests

Run all tests:

```powershell
python -m unittest discover -s tests -v
```

## Algorithm Notes

The search agent uses:

- depth-limited minimax
- alpha-beta pruning
- iterative deepening up to `max_depth`
- transposition table keyed by board, player, and depth
- move ordering
- candidate move filtering for larger boards

### Heuristic

For each contiguous line window of length `m`:

- if both players appear in the same window, that window scores `0`
- if only one player appears, the score grows exponentially with the count

The final score is:

- positive if favorable for the root player
- negative if favorable for the opponent
- adjusted by a mild center-control bonus

## Writeup Draft

A one-page draft is included here:

`writeup_one_pager.md`
