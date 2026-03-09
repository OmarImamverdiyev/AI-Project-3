from __future__ import annotations

import argparse
from dataclasses import dataclass

from .agent import MinimaxAgent, symbol_name
from .game import O, X, GameState, Move, Symbol


@dataclass(slots=True)
class MatchConfig:
    n: int
    m: int
    mode: str
    depth_x: int
    depth_o: int
    time_x: float
    time_o: float
    first: str


def parse_args() -> MatchConfig:
    parser = argparse.ArgumentParser(description="Generalized Tic Tac Toe")
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

    return MatchConfig(
        n=args.n,
        m=args.m,
        mode=args.mode,
        depth_x=args.depth_x,
        depth_o=args.depth_o,
        time_x=args.time_x,
        time_o=args.time_o,
        first=args.first,
    )


def main() -> None:
    cfg = parse_args()
    first = X if cfg.first == "x" else O
    state = GameState.new(n=cfg.n, m=cfg.m, first_player=first)

    agents: dict[Symbol, MinimaxAgent] = {
        X: MinimaxAgent(max_depth=cfg.depth_x, time_limit_s=cfg.time_x),
        O: MinimaxAgent(max_depth=cfg.depth_o, time_limit_s=cfg.time_o),
    }

    print(f"Generalized Tic Tac Toe: {cfg.n}x{cfg.n}, target={cfg.m}")
    print(f"Mode: {cfg.mode}, first player: {symbol_name(first)}")

    while not state.is_terminal():
        print()
        print(state.pretty_str())
        current = state.current_player
        print(f"Turn: {symbol_name(current)}")

        if cfg.mode == "human-vs-ai" and current == X:
            move = read_human_move(state)
        else:
            agent = agents[current]
            move = agent.choose_move(state)
            print(
                f"AI ({symbol_name(current)}) plays {move} "
                f"[nodes={agent.nodes_searched}, depth={agent.max_depth}]"
            )

        state = state.apply_move(move)

    print()
    print(state.pretty_str())
    outcome = state.outcome()
    if outcome == X:
        print("Winner: X")
    elif outcome == O:
        print("Winner: O")
    else:
        print("Draw")


def read_human_move(state: GameState) -> Move:
    while True:
        raw = input("Enter move as 'row col': ").strip()
        parts = raw.split()
        if len(parts) != 2:
            print("Please enter exactly two integers.")
            continue
        try:
            row = int(parts[0])
            col = int(parts[1])
        except ValueError:
            print("Please enter valid integers.")
            continue
        if not state.in_bounds(row, col):
            print("Move is out of bounds.")
            continue
        if state.at(row, col) != 0:
            print("Cell is already occupied.")
            continue
        return row, col


if __name__ == "__main__":
    main()
