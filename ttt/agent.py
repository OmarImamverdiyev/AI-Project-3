from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from .game import EMPTY, GameState, Move, Symbol, X

WIN_SCORE = 10_000_000


class SearchTimeout(Exception):
    """Raised when search exceeds the configured time budget."""


@dataclass(slots=True)
class MinimaxAgent:
    """Generalized Tic Tac Toe agent using alpha-beta minimax."""

    max_depth: int = 4
    time_limit_s: float = 1.5
    use_iterative_deepening: bool = True
    use_candidate_moves: bool = True
    transposition_table: dict[tuple[tuple[Symbol, ...], Symbol, int], int] = field(
        default_factory=dict
    )
    nodes_searched: int = 0

    def choose_move(self, state: GameState) -> Move:
        legal = state.legal_moves()
        if not legal:
            raise ValueError("no legal moves available")
        if len(legal) == state.n * state.n:
            center = state.n // 2
            return center, center

        deadline = time.perf_counter() + self.time_limit_s
        self.nodes_searched = 0
        self.transposition_table.clear()

        # Keep a deterministic fallback even if we timeout very early.
        fallback = self._ordered_moves(state, legal, root_player=state.current_player)[0]
        best_move = fallback

        if not self.use_iterative_deepening:
            depth = self.max_depth
            score, move = self._root_search(state, depth, deadline)
            if move is not None:
                best_move = move
            return best_move

        for depth in range(1, self.max_depth + 1):
            try:
                _, move = self._root_search(state, depth, deadline)
                if move is not None:
                    best_move = move
            except SearchTimeout:
                break
        return best_move

    def _root_search(
        self, state: GameState, depth: int, deadline: float
    ) -> tuple[int, Optional[Move]]:
        self._check_timeout(deadline)
        alpha = -math.inf
        beta = math.inf
        best_score = -math.inf
        best_move: Optional[Move] = None
        root_player = state.current_player

        legal = self._candidate_moves(state) if self.use_candidate_moves else state.legal_moves()
        for move in self._ordered_moves(state, legal, root_player=root_player):
            next_state = state.apply_move(move)
            score = self._minimax(
                state=next_state,
                depth=depth - 1,
                alpha=alpha,
                beta=beta,
                root_player=root_player,
                deadline=deadline,
            )
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
        return int(best_score), best_move

    def _minimax(
        self,
        state: GameState,
        depth: int,
        alpha: float,
        beta: float,
        root_player: Symbol,
        deadline: float,
    ) -> int:
        self.nodes_searched += 1
        self._check_timeout(deadline)

        key = (state.board, state.current_player, depth)
        cached = self.transposition_table.get(key)
        if cached is not None:
            return cached

        if state.is_terminal():
            val = self._terminal_value(state, root_player, depth)
            self.transposition_table[key] = val
            return val
        if depth == 0:
            val = self._evaluate(state, root_player)
            self.transposition_table[key] = val
            return val

        legal = self._candidate_moves(state) if self.use_candidate_moves else state.legal_moves()
        if state.current_player == root_player:
            value = -math.inf
            for move in self._ordered_moves(state, legal, root_player=root_player):
                value = max(
                    value,
                    self._minimax(
                        state.apply_move(move),
                        depth - 1,
                        alpha,
                        beta,
                        root_player,
                        deadline,
                    ),
                )
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
        else:
            value = math.inf
            for move in self._ordered_moves(state, legal, root_player=root_player):
                value = min(
                    value,
                    self._minimax(
                        state.apply_move(move),
                        depth - 1,
                        alpha,
                        beta,
                        root_player,
                        deadline,
                    ),
                )
                beta = min(beta, value)
                if alpha >= beta:
                    break

        out = int(value)
        self.transposition_table[key] = out
        return out

    def _check_timeout(self, deadline: float) -> None:
        if time.perf_counter() > deadline:
            raise SearchTimeout

    def _terminal_value(self, state: GameState, root_player: Symbol, depth: int) -> int:
        if state.winner is None:
            return 0
        # Prefer earlier wins and later losses.
        bonus = depth
        if state.winner == root_player:
            return WIN_SCORE + bonus
        return -WIN_SCORE - bonus

    def _evaluate(self, state: GameState, root_player: Symbol) -> int:
        return _heuristic_window_score(state, root_player)

    def _candidate_moves(self, state: GameState) -> list[Move]:
        legal = state.legal_moves()
        if len(legal) <= 12:
            return legal
        occupied = list(state.occupied_cells())
        if not occupied:
            return legal

        neighbor_moves: set[Move] = set()
        for r, c in occupied:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < state.n and 0 <= nc < state.n and state.at(nr, nc) == EMPTY:
                        neighbor_moves.add((nr, nc))
        if neighbor_moves:
            return list(neighbor_moves)
        return legal

    def _ordered_moves(
        self, state: GameState, moves: list[Move], root_player: Symbol
    ) -> list[Move]:
        # Move ordering improves alpha-beta pruning and speed.
        center = (state.n - 1) / 2

        def ordering_key(move: Move) -> tuple[int, float]:
            child = state.apply_move(move)
            tactical = 0
            if child.winner == state.current_player:
                tactical = (
                    1_000_000 if state.current_player == root_player else -1_000_000
                )
            static = self._evaluate(child, root_player)
            dist = abs(move[0] - center) + abs(move[1] - center)
            return tactical + static, -dist

        reverse = state.current_player == root_player
        return sorted(moves, key=ordering_key, reverse=reverse)


@lru_cache(maxsize=64)
def _windows_for(n: int, m: int) -> tuple[tuple[int, ...], ...]:
    windows: list[tuple[int, ...]] = []
    # Horizontal
    for r in range(n):
        for c0 in range(n - m + 1):
            windows.append(tuple(r * n + (c0 + k) for k in range(m)))
    # Vertical
    for c in range(n):
        for r0 in range(n - m + 1):
            windows.append(tuple((r0 + k) * n + c for k in range(m)))
    # Main diagonal
    for r0 in range(n - m + 1):
        for c0 in range(n - m + 1):
            windows.append(tuple((r0 + k) * n + (c0 + k) for k in range(m)))
    # Anti diagonal
    for r0 in range(n - m + 1):
        for c0 in range(m - 1, n):
            windows.append(tuple((r0 + k) * n + (c0 - k) for k in range(m)))
    return tuple(windows)


def _heuristic_window_score(state: GameState, root_player: Symbol) -> int:
    board = state.board
    opp = -root_player

    # Exponential growth gives stronger preference to near-complete lines.
    own_weight = [0] + [4 ** k for k in range(1, state.m + 1)]
    opp_weight = [0] + [4 ** k for k in range(1, state.m + 1)]

    score = 0
    for window in _windows_for(state.n, state.m):
        own = 0
        their = 0
        for idx in window:
            val = board[idx]
            if val == root_player:
                own += 1
            elif val == opp:
                their += 1
        if own > 0 and their > 0:
            continue
        if own > 0:
            score += own_weight[own]
        elif their > 0:
            score -= opp_weight[their]

    # Mild center preference to improve opening play.
    center = (state.n - 1) / 2
    for idx, val in enumerate(board):
        if val == EMPTY:
            continue
        r, c = divmod(idx, state.n)
        center_bonus = state.n - int(abs(r - center) + abs(c - center))
        if val == root_player:
            score += center_bonus
        else:
            score -= center_bonus

    return score


def symbol_name(symbol: Symbol) -> str:
    return "X" if symbol == X else "O"
