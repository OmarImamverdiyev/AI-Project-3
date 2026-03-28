# How To Start A Game

This file shows the exact commands needed to start a live AI P2P game against another team.

## Before You Start

Make sure your local `.env` file exists and contains at least:

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

Meaning:

- `AIP2P_TEAM_ID`
  Your team ID
- `AIP2P_OPPONENT_TEAM_ID`
  The team you want to play against
- `AIP2P_BOARD_SIZE`
  Board size
- `AIP2P_TARGET`
  How many in a row are needed to win

## Start A New Game Against An Opponent

### 1. Set the opponent team ID in `.env`

Open `.env` and change:

```text
AIP2P_OPPONENT_TEAM_ID=1492
```

If you want a different board setting, also change:

```text
AIP2P_BOARD_SIZE=5
AIP2P_TARGET=4
```

Examples:

- `3x3` normal Tic Tac Toe:

```text
AIP2P_BOARD_SIZE=3
AIP2P_TARGET=3
```

- `5x5` with target `4`:

```text
AIP2P_BOARD_SIZE=5
AIP2P_TARGET=4
```

### 2. Create the game

Run:

```powershell
python -m ttt.p2p_cli create-game
```

Expected output:

```text
Created game 5500
Updated .env with the new game defaults.
```

Important:

- the command reads your team ID, opponent team ID, board size, and target from `.env`
- after success, it automatically writes the new `AIP2P_GAME_ID` into `.env`

### 3. Check that the game exists

Run:

```powershell
python -m ttt.p2p_cli game-details
```

This shows:

- both teams
- board size and target
- whose turn it is
- the current board

### 4. Start automatic play

Run:

```powershell
python -m ttt.p2p_cli play-loop
```

What this does:

- keeps checking the game
- waits if it is the opponent's turn
- automatically submits a move when it becomes your turn

Stop it with:

```text
Ctrl+C
```

## Useful Extra Commands

### Show the board only

```powershell
python -m ttt.p2p_cli board
```

### Show recent moves

```powershell
python -m ttt.p2p_cli moves --count 10
```

### Make only one move and exit

```powershell
python -m ttt.p2p_cli auto-move
```

Use `auto-move` if you want one move only.

Use `play-loop` if you want the bot to keep playing the match automatically.

## Example Full Workflow

Suppose you want to play against team `1492` on a `5x5` board with target `4`.

### In `.env`

```text
AIP2P_OPPONENT_TEAM_ID=1492
AIP2P_BOARD_SIZE=5
AIP2P_TARGET=4
```

### Then run

```powershell
python -m ttt.p2p_cli create-game
python -m ttt.p2p_cli game-details
python -m ttt.p2p_cli play-loop
```

## If Another Team Starts The Game

If another team creates a game with your team, you do not need to create it yourself.

Use:

```powershell
python -m ttt.p2p_cli my-games
```

Then set the game ID in `.env`:

```text
AIP2P_GAME_ID=GAME_ID_HERE
```

Then run:

```powershell
python -m ttt.p2p_cli game-details
python -m ttt.p2p_cli play-loop
```

## Common Problems

### The opponent does not move

The server is passive. It will wait forever until the opponent sends their move.

### Temporary API reset errors

If the server briefly resets the connection, `play-loop` now retries and keeps going.

### Need to switch to a different opponent

Edit `.env`:

```text
AIP2P_OPPONENT_TEAM_ID=NEW_TEAM_ID
AIP2P_GAME_ID=
```

Then create a fresh game again:

```powershell
python -m ttt.p2p_cli create-game
```
