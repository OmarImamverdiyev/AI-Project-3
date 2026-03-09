from __future__ import annotations

import argparse
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Optional

from .agent import MinimaxAgent, symbol_name
from .game import EMPTY, O, X, GameState, Move, Symbol


@dataclass(slots=True)
class UIConfig:
    n: int
    m: int
    mode: str
    depth_x: int
    depth_o: int
    time_x: float
    time_o: float
    first: str


def parse_args() -> UIConfig:
    parser = argparse.ArgumentParser(description="Generalized Tic Tac Toe UI")
    parser.add_argument("--n", type=int, default=3, help="Board size")
    parser.add_argument("--m", type=int, default=3, help="Consecutive symbols required to win")
    parser.add_argument(
        "--mode",
        choices=["human-vs-ai", "ai-vs-ai"],
        default="human-vs-ai",
        help="Play mode",
    )
    parser.add_argument("--depth-x", type=int, default=4, help="Search depth for X")
    parser.add_argument("--depth-o", type=int, default=4, help="Search depth for O")
    parser.add_argument("--time-x", type=float, default=1.5, help="Time limit (sec) for X")
    parser.add_argument("--time-o", type=float, default=1.5, help="Time limit (sec) for O")
    parser.add_argument(
        "--first",
        choices=["x", "o"],
        default="x",
        help="Which side starts",
    )
    args = parser.parse_args()
    return UIConfig(
        n=args.n,
        m=args.m,
        mode=args.mode,
        depth_x=args.depth_x,
        depth_o=args.depth_o,
        time_x=args.time_x,
        time_o=args.time_o,
        first=args.first,
    )


class TicTacToeUI:
    def __init__(self, root: tk.Tk, cfg: UIConfig):
        self.root = root
        self.root.title("Generalized Tic Tac Toe")
        self.root.resizable(False, False)

        self.n_var = tk.StringVar(value=str(cfg.n))
        self.m_var = tk.StringVar(value=str(cfg.m))
        self.mode_var = tk.StringVar(value=cfg.mode)
        self.first_var = tk.StringVar(value=cfg.first)
        self.depth_x_var = tk.StringVar(value=str(cfg.depth_x))
        self.depth_o_var = tk.StringVar(value=str(cfg.depth_o))
        self.time_x_var = tk.StringVar(value=str(cfg.time_x))
        self.time_o_var = tk.StringVar(value=str(cfg.time_o))
        self.status_var = tk.StringVar(value="")

        self.state = GameState.new(n=cfg.n, m=cfg.m, first_player=X if cfg.first == "x" else O)
        self.agents: dict[Symbol, MinimaxAgent] = {
            X: MinimaxAgent(max_depth=cfg.depth_x, time_limit_s=cfg.time_x),
            O: MinimaxAgent(max_depth=cfg.depth_o, time_limit_s=cfg.time_o),
        }
        self.board_buttons: list[list[tk.Button]] = []
        self.ai_job: Optional[str] = None

        self._build_layout()
        self._start_new_game()

    def _build_layout(self) -> None:
        controls = ttk.Frame(self.root, padding=10)
        controls.grid(row=0, column=0, sticky="ew")

        ttk.Label(controls, text="N").grid(row=0, column=0, padx=4, pady=2)
        ttk.Entry(controls, textvariable=self.n_var, width=5).grid(row=0, column=1, padx=4, pady=2)
        ttk.Label(controls, text="M").grid(row=0, column=2, padx=4, pady=2)
        ttk.Entry(controls, textvariable=self.m_var, width=5).grid(row=0, column=3, padx=4, pady=2)

        ttk.Label(controls, text="Mode").grid(row=0, column=4, padx=4, pady=2)
        ttk.Combobox(
            controls,
            textvariable=self.mode_var,
            values=("human-vs-ai", "ai-vs-ai"),
            width=12,
            state="readonly",
        ).grid(row=0, column=5, padx=4, pady=2)

        ttk.Label(controls, text="First").grid(row=0, column=6, padx=4, pady=2)
        ttk.Combobox(
            controls,
            textvariable=self.first_var,
            values=("x", "o"),
            width=4,
            state="readonly",
        ).grid(row=0, column=7, padx=4, pady=2)

        ttk.Label(controls, text="Depth X/O").grid(row=1, column=0, padx=4, pady=2)
        ttk.Entry(controls, textvariable=self.depth_x_var, width=5).grid(
            row=1, column=1, padx=4, pady=2
        )
        ttk.Entry(controls, textvariable=self.depth_o_var, width=5).grid(
            row=1, column=2, padx=4, pady=2
        )

        ttk.Label(controls, text="Time X/O").grid(row=1, column=3, padx=4, pady=2)
        ttk.Entry(controls, textvariable=self.time_x_var, width=7).grid(
            row=1, column=4, padx=4, pady=2
        )
        ttk.Entry(controls, textvariable=self.time_o_var, width=7).grid(
            row=1, column=5, padx=4, pady=2
        )

        ttk.Button(controls, text="New Game", command=self._start_new_game).grid(
            row=1, column=7, padx=4, pady=2
        )

        board_wrapper = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        board_wrapper.grid(row=1, column=0)
        self.board_frame = ttk.Frame(board_wrapper)
        self.board_frame.grid(row=0, column=0)

        status = ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            padding=(10, 0, 10, 10),
        )
        status.grid(row=2, column=0, sticky="ew")

    def _read_config(self) -> Optional[UIConfig]:
        try:
            cfg = UIConfig(
                n=int(self.n_var.get()),
                m=int(self.m_var.get()),
                mode=self.mode_var.get(),
                depth_x=int(self.depth_x_var.get()),
                depth_o=int(self.depth_o_var.get()),
                time_x=float(self.time_x_var.get()),
                time_o=float(self.time_o_var.get()),
                first=self.first_var.get(),
            )
        except ValueError:
            messagebox.showerror("Invalid config", "N, M, depth, and time must be numeric.")
            return None

        if cfg.n <= 0 or cfg.m <= 0:
            messagebox.showerror("Invalid config", "N and M must be greater than 0.")
            return None
        if cfg.m > cfg.n:
            messagebox.showerror("Invalid config", "M cannot be greater than N.")
            return None
        if cfg.depth_x <= 0 or cfg.depth_o <= 0:
            messagebox.showerror("Invalid config", "Depth values must be greater than 0.")
            return None
        if cfg.time_x <= 0 or cfg.time_o <= 0:
            messagebox.showerror("Invalid config", "Time values must be greater than 0.")
            return None
        if cfg.mode not in {"human-vs-ai", "ai-vs-ai"}:
            messagebox.showerror("Invalid config", "Unsupported mode selected.")
            return None
        if cfg.first not in {"x", "o"}:
            messagebox.showerror("Invalid config", "First player must be x or o.")
            return None
        return cfg

    def _start_new_game(self) -> None:
        cfg = self._read_config()
        if cfg is None:
            return
        self._cancel_ai_job()

        first = X if cfg.first == "x" else O
        self.state = GameState.new(n=cfg.n, m=cfg.m, first_player=first)
        self.agents = {
            X: MinimaxAgent(max_depth=cfg.depth_x, time_limit_s=cfg.time_x),
            O: MinimaxAgent(max_depth=cfg.depth_o, time_limit_s=cfg.time_o),
        }
        self._build_board(cfg.n)
        self._refresh_board()
        self._update_status()
        self._schedule_ai_turn_if_needed()

    def _build_board(self, n: int) -> None:
        for child in self.board_frame.winfo_children():
            child.destroy()
        self.board_buttons = []

        for r in range(n):
            row_buttons: list[tk.Button] = []
            for c in range(n):
                button = tk.Button(
                    self.board_frame,
                    text=" ",
                    width=3,
                    height=1,
                    font=("Segoe UI", 18, "bold"),
                    command=lambda rr=r, cc=c: self._on_cell_click(rr, cc),
                )
                button.grid(row=r, column=c, padx=2, pady=2)
                row_buttons.append(button)
            self.board_buttons.append(row_buttons)

    def _on_cell_click(self, row: int, col: int) -> None:
        if self.state.is_terminal():
            return
        if not self._is_human_turn():
            return
        if self.state.at(row, col) != EMPTY:
            return

        self.state = self.state.apply_move((row, col))
        self._refresh_board()
        if self.state.is_terminal():
            self._announce_outcome()
            return
        self._update_status()
        self._schedule_ai_turn_if_needed()

    def _is_human_turn(self) -> bool:
        return self.mode_var.get() == "human-vs-ai" and self.state.current_player == X

    def _schedule_ai_turn_if_needed(self) -> None:
        if self.state.is_terminal():
            return
        if self.ai_job is not None:
            return
        if self.mode_var.get() == "human-vs-ai" and self.state.current_player == X:
            return
        self.status_var.set(f"Turn: {symbol_name(self.state.current_player)} (AI thinking...)")
        self.ai_job = self.root.after(100, self._run_ai_turn)

    def _run_ai_turn(self) -> None:
        self.ai_job = None
        if self.state.is_terminal():
            return
        if self.mode_var.get() == "human-vs-ai" and self.state.current_player == X:
            return

        player = self.state.current_player
        agent = self.agents[player]
        move = agent.choose_move(self.state)
        self.state = self.state.apply_move(move)
        self._refresh_board()

        if self.state.is_terminal():
            self._announce_outcome()
            return

        self.status_var.set(
            f"AI {symbol_name(player)} -> {move} "
            f"[nodes={agent.nodes_searched}, depth={agent.max_depth}]"
        )
        self._schedule_ai_turn_if_needed()

    def _refresh_board(self) -> None:
        for r in range(self.state.n):
            for c in range(self.state.n):
                symbol = self.state.at(r, c)
                text = " "
                if symbol == X:
                    text = "X"
                elif symbol == O:
                    text = "O"
                self.board_buttons[r][c].configure(text=text)

        human_active = self._is_human_turn() and not self.state.is_terminal()
        for r in range(self.state.n):
            for c in range(self.state.n):
                can_click = human_active and self.state.at(r, c) == EMPTY
                self.board_buttons[r][c].configure(state=tk.NORMAL if can_click else tk.DISABLED)

    def _update_status(self) -> None:
        if self.state.is_terminal():
            self._announce_outcome()
            return

        if self._is_human_turn():
            self.status_var.set("Your turn (X).")
        else:
            self.status_var.set(f"Turn: {symbol_name(self.state.current_player)}")

    def _announce_outcome(self) -> None:
        outcome = self.state.outcome()
        if outcome == X:
            message = "Winner: X"
        elif outcome == O:
            message = "Winner: O"
        else:
            message = "Draw"
        self.status_var.set(message)
        messagebox.showinfo("Game Over", message)

    def _cancel_ai_job(self) -> None:
        if self.ai_job is not None:
            self.root.after_cancel(self.ai_job)
            self.ai_job = None


def main() -> None:
    cfg = parse_args()
    root = tk.Tk()
    TicTacToeUI(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()
