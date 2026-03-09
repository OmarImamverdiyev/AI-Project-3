from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

Symbol = int
Move = tuple[int, int]

EMPTY: Symbol = 0
X: Symbol = 1
O: Symbol = -1

SYMBOL_TO_CHAR = {X: "X", O: "O", EMPTY: "."}


@dataclass(frozen=True, slots=True)
class GameState:
    """Immutable state for generalized n x n Tic Tac Toe."""

    n: int
    m: int
    board: tuple[Symbol, ...]
    current_player: Symbol = X
    last_move: Optional[Move] = None
    winner: Optional[Symbol] = None

    @staticmethod
    def new(n: int, m: int, first_player: Symbol = X) -> "GameState":
        if n <= 0:
            raise ValueError("n must be > 0")
        if m <= 0:
            raise ValueError("m must be > 0")
        if m > n:
            raise ValueError("m cannot be greater than n")
        return GameState(
            n=n,
            m=m,
            board=tuple([EMPTY] * (n * n)),
            current_player=first_player,
            last_move=None,
            winner=None,
        )

    def index(self, row: int, col: int) -> int:
        return row * self.n + col

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.n and 0 <= col < self.n

    def at(self, row: int, col: int) -> Symbol:
        return self.board[self.index(row, col)]

    def is_full(self) -> bool:
        return EMPTY not in self.board

    def legal_moves(self) -> list[Move]:
        if self.winner is not None:
            return []
        moves: list[Move] = []
        for idx, value in enumerate(self.board):
            if value == EMPTY:
                moves.append((idx // self.n, idx % self.n))
        return moves

    def apply_move(self, move: Move) -> "GameState":
        row, col = move
        if not self.in_bounds(row, col):
            raise ValueError(f"move out of bounds: {move}")
        idx = self.index(row, col)
        if self.board[idx] != EMPTY:
            raise ValueError(f"cell already occupied: {move}")
        if self.winner is not None:
            raise ValueError("cannot move in a finished game")

        board_list = list(self.board)
        board_list[idx] = self.current_player
        next_board = tuple(board_list)

        maybe_winner = _winner_from_last_move(
            n=self.n,
            m=self.m,
            board=next_board,
            row=row,
            col=col,
            symbol=self.current_player,
        )
        return GameState(
            n=self.n,
            m=self.m,
            board=next_board,
            current_player=-self.current_player,
            last_move=move,
            winner=maybe_winner,
        )

    def is_terminal(self) -> bool:
        return self.winner is not None or self.is_full()

    def outcome(self) -> Optional[Symbol]:
        """Returns X, O, or None (draw or ongoing)."""
        if self.winner is not None:
            return self.winner
        if self.is_full():
            return EMPTY
        return None

    def board_str(self) -> str:
        rows = []
        for r in range(self.n):
            row_symbols = [SYMBOL_TO_CHAR[self.at(r, c)] for c in range(self.n)]
            rows.append(" ".join(row_symbols))
        return "\n".join(rows)

    def pretty_str(self) -> str:
        header = "   " + " ".join(f"{c:2d}" for c in range(self.n))
        rows = []
        for r in range(self.n):
            row_symbols = [SYMBOL_TO_CHAR[self.at(r, c)] for c in range(self.n)]
            rows.append(f"{r:2d} " + "  ".join(row_symbols))
        return header + "\n" + "\n".join(rows)

    def occupied_cells(self) -> Iterable[Move]:
        for idx, value in enumerate(self.board):
            if value != EMPTY:
                yield idx // self.n, idx % self.n


def _winner_from_last_move(
    n: int,
    m: int,
    board: tuple[Symbol, ...],
    row: int,
    col: int,
    symbol: Symbol,
) -> Optional[Symbol]:
    for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
        count = 1
        count += _count_one_direction(n, board, row, col, dr, dc, symbol)
        count += _count_one_direction(n, board, row, col, -dr, -dc, symbol)
        if count >= m:
            return symbol
    return None


def _count_one_direction(
    n: int,
    board: tuple[Symbol, ...],
    row: int,
    col: int,
    dr: int,
    dc: int,
    symbol: Symbol,
) -> int:
    count = 0
    r, c = row + dr, col + dc
    while 0 <= r < n and 0 <= c < n:
        idx = r * n + c
        if board[idx] != symbol:
            break
        count += 1
        r += dr
        c += dc
    return count
