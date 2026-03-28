from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .agent import MinimaxAgent, symbol_name
from .env_utils import env_float, env_int, env_str, load_dotenv, upsert_dotenv
from .game import O, X
from .p2p import ApiCredentials, P2PApiError, P2PClient, RemoteGameSnapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI P2P Tic Tac Toe helper")
    parser.add_argument(
        "--user-id",
        default=env_str("AIP2P_USER_ID"),
        help="AI P2P user ID. Defaults to .env/AIP2P_USER_ID.",
    )
    parser.add_argument(
        "--api-key",
        default=env_str("AIP2P_API_KEY"),
        help="AI P2P API key. Defaults to .env/AIP2P_API_KEY.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("my-teams", help="List your team IDs")

    create_team = subparsers.add_parser("create-team", help="Create a new team")
    create_team.add_argument("--name", required=True, help="New team name")

    add_member = subparsers.add_parser("add-member", help="Add a user to a team")
    add_member.add_argument(
        "--team-id",
        required=env_int("AIP2P_TEAM_ID") is None,
        default=env_int("AIP2P_TEAM_ID"),
        type=int,
        help="Team ID. Defaults to .env/AIP2P_TEAM_ID.",
    )
    add_member.add_argument("--member-user-id", required=True, type=int)

    remove_member = subparsers.add_parser("remove-member", help="Remove a user from a team")
    remove_member.add_argument(
        "--team-id",
        required=env_int("AIP2P_TEAM_ID") is None,
        default=env_int("AIP2P_TEAM_ID"),
        type=int,
        help="Team ID. Defaults to .env/AIP2P_TEAM_ID.",
    )
    remove_member.add_argument("--member-user-id", required=True, type=int)

    team_members = subparsers.add_parser("team-members", help="List the members of a team")
    team_members.add_argument(
        "--team-id",
        required=env_int("AIP2P_TEAM_ID") is None,
        default=env_int("AIP2P_TEAM_ID"),
        type=int,
        help="Team ID. Defaults to .env/AIP2P_TEAM_ID.",
    )

    my_games = subparsers.add_parser("my-games", help="List your games")
    my_games.add_argument("--open-only", action="store_true", help="Only show open games")

    create_game = subparsers.add_parser("create-game", help="Create a new game")
    create_game.add_argument(
        "--team-id",
        required=env_int("AIP2P_TEAM_ID") is None,
        default=env_int("AIP2P_TEAM_ID"),
        type=int,
        help="Your team ID. Defaults to .env/AIP2P_TEAM_ID.",
    )
    create_game.add_argument(
        "--opponent-team-id",
        required=env_int("AIP2P_OPPONENT_TEAM_ID") is None,
        default=env_int("AIP2P_OPPONENT_TEAM_ID"),
        type=int,
        help="Opponent team ID. Defaults to .env/AIP2P_OPPONENT_TEAM_ID.",
    )
    create_game.add_argument(
        "--board-size",
        default=env_int("AIP2P_BOARD_SIZE"),
        type=int,
        help="Board size. Defaults to .env/AIP2P_BOARD_SIZE or the server default 12.",
    )
    create_game.add_argument(
        "--target",
        default=env_int("AIP2P_TARGET"),
        type=int,
        help="Target in a row. Defaults to .env/AIP2P_TARGET or the server default 6.",
    )

    game_details = subparsers.add_parser("game-details", help="Show game details")
    game_details.add_argument(
        "--game-id",
        required=env_int("AIP2P_GAME_ID") is None,
        default=env_int("AIP2P_GAME_ID"),
        type=int,
        help="Game ID. Defaults to .env/AIP2P_GAME_ID.",
    )

    board = subparsers.add_parser("board", help="Show a game board")
    board.add_argument(
        "--game-id",
        required=env_int("AIP2P_GAME_ID") is None,
        default=env_int("AIP2P_GAME_ID"),
        type=int,
        help="Game ID. Defaults to .env/AIP2P_GAME_ID.",
    )

    moves = subparsers.add_parser("moves", help="Show recent moves")
    moves.add_argument(
        "--game-id",
        required=env_int("AIP2P_GAME_ID") is None,
        default=env_int("AIP2P_GAME_ID"),
        type=int,
        help="Game ID. Defaults to .env/AIP2P_GAME_ID.",
    )
    moves.add_argument("--count", type=int, default=20)

    auto_move = subparsers.add_parser(
        "auto-move",
        help="Compute and submit exactly one move if it is your turn",
    )
    auto_move.add_argument(
        "--game-id",
        required=env_int("AIP2P_GAME_ID") is None,
        default=env_int("AIP2P_GAME_ID"),
        type=int,
        help="Game ID. Defaults to .env/AIP2P_GAME_ID.",
    )
    auto_move.add_argument(
        "--team-id",
        required=env_int("AIP2P_TEAM_ID") is None,
        default=env_int("AIP2P_TEAM_ID"),
        type=int,
        help="Team ID. Defaults to .env/AIP2P_TEAM_ID.",
    )
    auto_move.add_argument("--depth", type=int, default=env_int("AIP2P_DEPTH") or 3)
    auto_move.add_argument(
        "--time-limit",
        type=float,
        default=env_float("AIP2P_TIME_LIMIT") or 1.5,
    )

    play_loop = subparsers.add_parser(
        "play-loop",
        help="Poll a game and submit moves automatically when it is your turn",
    )
    play_loop.add_argument(
        "--game-id",
        required=env_int("AIP2P_GAME_ID") is None,
        default=env_int("AIP2P_GAME_ID"),
        type=int,
        help="Game ID. Defaults to .env/AIP2P_GAME_ID.",
    )
    play_loop.add_argument(
        "--team-id",
        required=env_int("AIP2P_TEAM_ID") is None,
        default=env_int("AIP2P_TEAM_ID"),
        type=int,
        help="Team ID. Defaults to .env/AIP2P_TEAM_ID.",
    )
    play_loop.add_argument("--depth", type=int, default=env_int("AIP2P_DEPTH") or 3)
    play_loop.add_argument(
        "--time-limit",
        type=float,
        default=env_float("AIP2P_TIME_LIMIT") or 1.5,
    )
    play_loop.add_argument(
        "--poll-seconds",
        type=float,
        default=env_float("AIP2P_POLL_SECONDS") or 5.0,
    )

    return parser


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    if not args.user_id or not args.api_key:
        parser.error(
            "Missing credentials. Pass --user-id/--api-key or set "
            "AIP2P_USER_ID and AIP2P_API_KEY in .env or the environment."
        )

    credentials = ApiCredentials(user_id=str(args.user_id), api_key=str(args.api_key))
    client = P2PClient(credentials)

    try:
        _dispatch(client, args)
    except P2PApiError as exc:
        print(f"API error: {exc}")
        raise SystemExit(1) from exc


def _dispatch(client: P2PClient, args: argparse.Namespace) -> None:
    if args.command == "my-teams":
        teams = client.my_teams()
        print(json.dumps({"myTeams": teams}, indent=2))
        return

    if args.command == "create-team":
        team_id = client.create_team(args.name)
        print(f"Created team {team_id}")
        return

    if args.command == "add-member":
        client.add_team_member(team_id=args.team_id, user_id=args.member_user_id)
        print(f"Added user {args.member_user_id} to team {args.team_id}")
        return

    if args.command == "remove-member":
        client.remove_team_member(team_id=args.team_id, user_id=args.member_user_id)
        print(f"Removed user {args.member_user_id} from team {args.team_id}")
        return

    if args.command == "team-members":
        members = client.team_members(args.team_id)
        print(json.dumps({"teamId": args.team_id, "userIds": members}, indent=2))
        return

    if args.command == "my-games":
        games = client.my_games(open_only=args.open_only)
        key = "myOpenGames" if args.open_only else "myGames"
        print(json.dumps({key: games}, indent=2))
        return

    if args.command == "create-game":
        game_id = client.create_game(
            team_id=args.team_id,
            opponent_team_id=args.opponent_team_id,
            board_size=args.board_size,
            target=args.target,
        )
        print(f"Created game {game_id}")
        _remember_game_defaults(args, game_id)
        return

    if args.command == "game-details":
        snapshot = client.snapshot(args.game_id)
        _print_snapshot(snapshot)
        return

    if args.command == "board":
        snapshot = client.snapshot(args.game_id)
        print(snapshot.state.pretty_str())
        return

    if args.command == "moves":
        recent_moves = client.moves(game_id=args.game_id, count=args.count)
        for move in recent_moves:
            print(
                f"moveId={move.move_id} teamId={move.team_id} "
                f"symbol={move.symbol or '?'} move={move.move}"
            )
        return

    if args.command == "auto-move":
        _auto_move(
            client,
            game_id=args.game_id,
            team_id=args.team_id,
            depth=args.depth,
            time_limit=args.time_limit,
        )
        return

    if args.command == "play-loop":
        _play_loop(
            client,
            game_id=args.game_id,
            team_id=args.team_id,
            depth=args.depth,
            time_limit=args.time_limit,
            poll_seconds=args.poll_seconds,
        )
        return

    raise ValueError(f"Unknown command: {args.command}")


def _auto_move(
    client: P2PClient,
    *,
    game_id: int,
    team_id: int,
    depth: int,
    time_limit: float,
) -> None:
    snapshot = client.snapshot(game_id)
    _print_snapshot(snapshot)

    if snapshot.details.winner_team_id is not None or snapshot.state.is_full():
        print("Game is already finished.")
        return
    if snapshot.details.turn_team_id != team_id:
        print(f"It is not team {team_id}'s turn right now.")
        return

    if team_id not in snapshot.details.participant_team_ids():
        raise P2PApiError(f"Team {team_id} is not a participant in game {game_id}.")

    agent = MinimaxAgent(max_depth=depth, time_limit_s=time_limit)
    move = agent.choose_move(snapshot.state)
    move_id = client.make_move(game_id=game_id, team_id=team_id, move=move)
    local_symbol = X if snapshot.symbol_for_team(team_id) == "X" else O
    print(
        f"Submitted move {move} as {symbol_name(local_symbol)} "
        f"[moveId={move_id}, nodes={agent.nodes_searched}, depth={agent.max_depth}]"
    )


def _play_loop(
    client: P2PClient,
    *,
    game_id: int,
    team_id: int,
    depth: int,
    time_limit: float,
    poll_seconds: float,
) -> None:
    last_seen: tuple[int, int | None, int | None] | None = None
    try:
        while True:
            try:
                snapshot = client.snapshot(game_id)
                current_signature = (
                    snapshot.details.move_count,
                    snapshot.details.turn_team_id,
                    snapshot.details.winner_team_id,
                )
                if current_signature != last_seen:
                    _print_snapshot(snapshot)
                    last_seen = current_signature

                if snapshot.details.winner_team_id is not None or snapshot.state.is_full():
                    print("Game finished.")
                    return

                if snapshot.details.turn_team_id == team_id:
                    _auto_move(
                        client,
                        game_id=game_id,
                        team_id=team_id,
                        depth=depth,
                        time_limit=time_limit,
                    )
                    time.sleep(1.0)
                    continue

                time.sleep(poll_seconds)
            except P2PApiError as exc:
                print(f"Temporary API issue: {exc}. Retrying in {poll_seconds:.1f}s...")
                time.sleep(poll_seconds)
    except KeyboardInterrupt:
        print("Stopped polling.")


def _print_snapshot(snapshot: RemoteGameSnapshot) -> None:
    details = snapshot.details
    print(
        "Game "
        f"{details.game_id}: {details.team1_name} ({details.team1_id}) vs "
        f"{details.team2_name} ({details.team2_id})"
    )
    print(
        f"Board {details.board_size}x{details.board_size}, target={details.target}, "
        f"moves={details.move_count}, status={details.status}"
    )
    print(
        f"Symbols: {details.team1_id}->{snapshot.symbol_by_team[details.team1_id]}, "
        f"{details.team2_id}->{snapshot.symbol_by_team[details.team2_id]}"
    )
    if details.turn_team_id is not None:
        print(f"Turn team: {details.turn_team_id}")
    if details.winner_team_id is not None:
        print(f"Winner team: {details.winner_team_id}")
    print(snapshot.state.pretty_str())


def _remember_game_defaults(args: argparse.Namespace, game_id: int) -> None:
    dotenv_path = Path(".env")
    if not dotenv_path.exists():
        return

    upsert_dotenv(
        dotenv_path,
        {
            "AIP2P_TEAM_ID": args.team_id,
            "AIP2P_OPPONENT_TEAM_ID": args.opponent_team_id,
            "AIP2P_GAME_ID": game_id,
            "AIP2P_BOARD_SIZE": args.board_size,
            "AIP2P_TARGET": args.target,
        },
    )
    print("Updated .env with the new game defaults.")


if __name__ == "__main__":
    main()
