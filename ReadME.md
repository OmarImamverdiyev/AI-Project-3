# AI Project 3 - Generalized Tic Tac Toe

This repository contains a local, API-independent implementation for the project:
- generalized `n x n` Tic Tac Toe
- configurable win target `m`
- minimax adversarial agent with alpha-beta pruning
- local CLI for `human-vs-ai` and `ai-vs-ai`

## Quick Start

```powershell
python -m ttt.cli --n 3 --m 3 --mode human-vs-ai --depth-x 4 --depth-o 4
```

`X` is the human side in `human-vs-ai` mode.

Run the Tkinter UI version:

```powershell
python -m ttt.ui --n 3 --m 3 --mode human-vs-ai --depth-x 4 --depth-o 4
```

## Useful Commands

Run AI vs AI:

```powershell
python -m ttt.cli --n 5 --m 4 --mode ai-vs-ai --depth-x 3 --depth-o 3 --time-x 1.0 --time-o 1.0
```

Start with O:

```powershell
python -m ttt.cli --n 4 --m 3 --mode ai-vs-ai --first o
```

Run tests:

```powershell
python -m unittest discover -s tests -v
```

## Algorithm Notes

The search agent uses:
- depth-limited minimax
- alpha-beta pruning
- iterative deepening up to `max_depth`
- transposition table keyed by board/player/depth
- move ordering (winning/tactical moves first)
- candidate move filtering to cells near existing symbols for large boards

### Heuristic (Evaluation Function)

For every contiguous line-window of length `m` across rows, columns, and diagonals:
- if both players appear in the window, score `0` for that window (blocked)
- if only one player appears, score grows exponentially with count (`4^k`)

The final score is:
- positive if favorable for the root player
- negative if favorable for the opponent
- plus a mild center-control bonus

## Writeup Draft

A ready-to-edit one-page draft is included in:

`writeup_one_pager.md`

You can export it to PDF via your preferred editor once you personalize team details and final results.
