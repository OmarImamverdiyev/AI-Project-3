# AI Project 3 - Generalized Tic Tac Toe

Team: `<team name>`  
Members: `<name 1>`, `<name 2>`, `<name 3>`

## 1) Evaluation (Heuristic) Function

Our heuristic evaluates every contiguous length-`m` window in all four directions (row, column, main diagonal, anti-diagonal). For each window:

- If both players appear, it is blocked and contributes `0`.
- If only our symbols appear (`k` symbols, rest empty), contribution is `+4^k`.
- If only opponent symbols appear (`k` symbols, rest empty), contribution is `-4^k`.

This makes near-complete lines much more valuable than short-term scattered control. We also add a small center-control bonus to improve opening quality on larger boards.

Terminal states override heuristic values:
- Win: large positive constant
- Loss: large negative constant
- Draw: `0`

## 2) Minimax / Adversarial Search Design

We use depth-limited minimax with alpha-beta pruning.

Key details:
- Iterative deepening: search depth increases from 1 to `max_depth`, preserving the best move found so far.
- Time budget per move: search stops safely at timeout and returns the latest complete-depth best move.
- Move ordering: tactical moves (especially immediate wins) and strong static candidates are explored first, increasing alpha-beta cutoffs.
- Transposition table: memoizes repeated board states to avoid re-solving equivalent subtrees.

This combination gives stronger play than fixed-order minimax at the same depth/time budget.

## 3) Performance Improvements / Tricks

1. Candidate-move filtering:
Only consider empty cells near existing pieces (8-neighborhood) when the board is large and sparse. This reduces branching factor substantially with little practical strength loss.

2. Window precomputation:
All length-`m` windows are precomputed once per `(n, m)`, reducing repeated overhead inside evaluation.

3. Tactical ordering:
Moves that produce immediate wins are prioritized, so pruning happens earlier and tactical opportunities are captured reliably.

4. Early game center bias:
Slight preference for central positions improves opening structure and keeps options flexible.

## 4) Notes for API Integration

Our local implementation is API-agnostic and can be wrapped with the course API later by mapping:
- incoming board state -> internal `GameState`
- legal move request -> `MinimaxAgent.choose_move`
- output move -> API action format

The search and heuristic modules are already separated from I/O, so integration should be straightforward.
