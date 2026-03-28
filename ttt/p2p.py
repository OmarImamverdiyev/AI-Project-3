from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlencode

from .env_utils import load_dotenv
from .game import EMPTY, O, X, GameState, Symbol

API_URL = "https://www.notexponential.com/aip2pgaming/api/index.php"
HTTP_STATUS_MARKER = "__HTTP_STATUS__:"
CURL_TRANSIENT_EXIT_CODES = {7, 18, 28, 35, 52, 55, 56}
HTTP_TRANSIENT_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


class P2PApiError(RuntimeError):
    """Raised when the AI P2P API returns an error payload."""

    def __init__(self, message: str, payload: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.payload = payload


@dataclass(frozen=True, slots=True)
class ApiCredentials:
    user_id: str
    api_key: str

    @staticmethod
    def from_env(env: Mapping[str, str] | None = None) -> "ApiCredentials":
        if env is None:
            load_dotenv()
        source = env if env is not None else os.environ
        user_id = source.get("AIP2P_USER_ID", "").strip()
        api_key = source.get("AIP2P_API_KEY", "").strip()
        if not user_id or not api_key:
            raise ValueError(
                "Missing credentials. Set AIP2P_USER_ID and AIP2P_API_KEY "
                "in .env or the environment, or pass them on the command line."
            )
        return ApiCredentials(user_id=user_id, api_key=api_key)


@dataclass(frozen=True, slots=True)
class RemoteMove:
    move_id: int
    game_id: int
    team_id: int
    move: tuple[int, int]
    symbol: str | None
    move_x: int | None = None
    move_y: int | None = None


@dataclass(frozen=True, slots=True)
class RemoteGameDetails:
    game_id: int
    game_type: str
    move_count: int
    board_size: int
    target: int
    team1_id: int
    team1_name: str
    team2_id: int
    team2_name: str
    seconds_per_move: int | None
    status: str
    winner_team_id: int | None
    turn_team_id: int | None

    def participant_team_ids(self) -> tuple[int, int]:
        return self.team1_id, self.team2_id

    def team_name(self, team_id: int) -> str:
        if team_id == self.team1_id:
            return self.team1_name
        if team_id == self.team2_id:
            return self.team2_name
        raise KeyError(f"team {team_id} is not part of game {self.game_id}")


@dataclass(frozen=True, slots=True)
class RemoteGameSnapshot:
    details: RemoteGameDetails
    board_map: dict[tuple[int, int], str]
    state: GameState
    symbol_by_team: dict[int, str]
    recent_moves: list[RemoteMove]

    def symbol_for_team(self, team_id: int) -> str:
        if team_id not in self.symbol_by_team:
            raise KeyError(f"team {team_id} is not part of game {self.details.game_id}")
        return self.symbol_by_team[team_id]


class P2PClient:
    """Thin client for the AI P2P game server using curl as transport.

    In this environment, direct Python HTTP libraries were rejected by the
    server's ModSecurity layer while curl worked reliably, so the client uses
    curl for transport and handles JSON parsing in Python.
    """

    def __init__(
        self,
        credentials: ApiCredentials,
        *,
        base_url: str = API_URL,
        curl_binary: str | None = None,
        max_get_retries: int = 2,
        retry_backoff_s: float = 1.0,
    ) -> None:
        self.credentials = credentials
        self.base_url = base_url
        self.curl_binary = curl_binary or shutil.which("curl.exe") or shutil.which("curl")
        self.max_get_retries = max_get_retries
        self.retry_backoff_s = retry_backoff_s
        if not self.curl_binary:
            raise RuntimeError("curl is required to use the AI P2P API client.")

    def my_teams(self) -> list[int]:
        payload = self._request_json("GET", {"type": "myTeams"})
        return _as_int_list(payload.get("myTeams"))

    def create_team(self, name: str) -> int:
        payload = self._request_json("POST", {"type": "team", "name": name})
        return _require_int(payload, "teamId")

    def add_team_member(self, team_id: int, user_id: int) -> None:
        self._request_json(
            "POST",
            {"type": "member", "teamId": team_id, "userId": user_id},
        )

    def remove_team_member(self, team_id: int, user_id: int) -> None:
        self._request_json(
            "POST",
            {"type": "removeMember", "teamId": team_id, "userId": user_id},
        )

    def team_members(self, team_id: int) -> list[int]:
        payload = self._request_json("GET", {"type": "team", "teamId": team_id})
        return _as_int_list(payload.get("userIds"))

    def my_games(self, *, open_only: bool = False) -> list[int]:
        kind = "myOpenGames" if open_only else "myGames"
        payload = self._request_json("GET", {"type": kind})
        return _as_int_list(payload.get("myGames"))

    def create_game(
        self,
        *,
        team_id: int,
        opponent_team_id: int,
        board_size: int | None = None,
        target: int | None = None,
    ) -> int:
        params: dict[str, Any] = {
            "type": "game",
            "teamId1": team_id,
            "teamId2": opponent_team_id,
            "gameType": "TTT",
        }
        if board_size is not None:
            params["boardSize"] = board_size
        if target is not None:
            params["target"] = target
        payload = self._request_json("POST", params)
        return _require_int(payload, "gameId")

    def make_move(self, *, game_id: int, team_id: int, move: tuple[int, int]) -> int:
        move_text = f"{move[0]},{move[1]}"
        payload = self._request_json(
            "POST",
            {"type": "move", "gameId": game_id, "teamId": team_id, "move": move_text},
        )
        return _require_int(payload, "moveId")

    def moves(self, *, game_id: int, count: int = 20) -> list[RemoteMove]:
        payload = self._request_json(
            "GET",
            {"type": "moves", "gameId": game_id, "count": count},
        )
        raw_moves = payload.get("moves") or []
        if not isinstance(raw_moves, list):
            raise P2PApiError("Expected 'moves' to be a list.", payload)
        return [parse_remote_move(item) for item in raw_moves]

    def game_details(self, game_id: int) -> RemoteGameDetails:
        payload = self._request_json("GET", {"type": "gameDetails", "gameId": game_id})
        return parse_game_details_payload(payload)

    def board_string(self, game_id: int) -> str:
        payload = self._request_json("GET", {"type": "boardString", "gameId": game_id})
        output = payload.get("output")
        if not isinstance(output, str):
            raise P2PApiError("Expected 'output' to be a string.", payload)
        return output

    def board_map(self, game_id: int) -> dict[tuple[int, int], str]:
        payload = self._request_json("GET", {"type": "boardMap", "gameId": game_id})
        return parse_board_map_payload(payload)

    def snapshot(self, game_id: int) -> RemoteGameSnapshot:
        details = self.game_details(game_id)
        board_map = self.board_map(game_id)
        recent_moves: list[RemoteMove] = []
        if details.move_count > 0:
            recent_moves = self.moves(game_id=game_id, count=1)
        symbol_by_team = infer_symbol_by_team(details, recent_moves)
        state = build_game_state(details, board_map, symbol_by_team)
        return RemoteGameSnapshot(
            details=details,
            board_map=board_map,
            state=state,
            symbol_by_team=symbol_by_team,
            recent_moves=recent_moves,
        )

    def _request_json(self, method: str, params: Mapping[str, Any]) -> dict[str, Any]:
        raw = self._request(method, params)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise P2PApiError(f"Expected JSON response, got: {raw[:200]!r}") from exc
        if not isinstance(payload, dict):
            raise P2PApiError(f"Expected JSON object, got {type(payload).__name__}.")
        code = payload.get("code")
        if code != "OK":
            message = payload.get("message") or f"API returned code={code!r}"
            raise P2PApiError(message, payload)
        return payload

    def _request(self, method: str, params: Mapping[str, Any]) -> str:
        method_upper = method.upper()
        if method_upper not in {"GET", "POST"}:
            raise ValueError(f"Unsupported HTTP method: {method}")

        max_attempts = self.max_get_retries + 1 if method_upper == "GET" else 1
        last_error: P2PApiError | None = None

        for attempt in range(1, max_attempts + 1):
            args = [
                self.curl_binary,
                "--silent",
                "--show-error",
                "--location",
                "--http1.1",
                "--header",
                f"userId: {self.credentials.user_id}",
                "--header",
                f"x-api-key: {self.credentials.api_key}",
                "--header",
                "Accept: application/json",
                "--write-out",
                f"\n{HTTP_STATUS_MARKER}%{{http_code}}",
            ]

            if method_upper == "GET":
                query = urlencode(_stringify_mapping(params))
                url = self.base_url if not query else f"{self.base_url}?{query}"
                args.extend(["--request", "GET", "--url", url])
            else:
                args.extend(
                    [
                        "--request",
                        "POST",
                        "--url",
                        self.base_url,
                        "--header",
                        "Content-Type: application/x-www-form-urlencoded",
                    ]
                )
                for key, value in _stringify_mapping(params).items():
                    args.extend(["--data-urlencode", f"{key}={value}"])

            proc = subprocess.run(args, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                message = proc.stderr.strip() or proc.stdout.strip() or "curl request failed"
                error = P2PApiError(message)
                if _should_retry_request(
                    method_upper,
                    curl_exit_code=proc.returncode,
                    http_status_code=None,
                    attempt=attempt,
                    max_attempts=max_attempts,
                ):
                    last_error = error
                    time.sleep(self.retry_backoff_s * attempt)
                    continue
                raise error

            if HTTP_STATUS_MARKER not in proc.stdout:
                error = P2PApiError("Could not determine HTTP status from curl response.")
                if _should_retry_request(
                    method_upper,
                    curl_exit_code=None,
                    http_status_code=None,
                    attempt=attempt,
                    max_attempts=max_attempts,
                ):
                    last_error = error
                    time.sleep(self.retry_backoff_s * attempt)
                    continue
                raise error

            body, _, suffix = proc.stdout.rpartition(HTTP_STATUS_MARKER)
            status_text = suffix.strip()
            try:
                status_code = int(status_text)
            except ValueError as exc:
                error = P2PApiError(
                    f"Could not parse HTTP status from curl response: {status_text!r}"
                )
                if _should_retry_request(
                    method_upper,
                    curl_exit_code=None,
                    http_status_code=None,
                    attempt=attempt,
                    max_attempts=max_attempts,
                ):
                    last_error = error
                    time.sleep(self.retry_backoff_s * attempt)
                    continue
                raise error from exc

            cleaned_body = body.rstrip()
            if status_code >= 400:
                error = P2PApiError(f"HTTP {status_code}: {cleaned_body[:200]}")
                if _should_retry_request(
                    method_upper,
                    curl_exit_code=None,
                    http_status_code=status_code,
                    attempt=attempt,
                    max_attempts=max_attempts,
                ):
                    last_error = error
                    time.sleep(self.retry_backoff_s * attempt)
                    continue
                raise error
            return cleaned_body

        if last_error is not None:
            raise last_error
        raise P2PApiError("Request failed after retries.")


def parse_remote_move(raw_move: Mapping[str, Any]) -> RemoteMove:
    move_text = _require_value(raw_move, "move")
    move = parse_move_text(str(move_text))
    symbol = raw_move.get("symbol")
    symbol_text = str(symbol).upper() if symbol not in (None, "") else None
    return RemoteMove(
        move_id=_coerce_int(_require_value(raw_move, "moveId")),
        game_id=_coerce_int(_require_value(raw_move, "gameId")),
        team_id=_coerce_int(_require_value(raw_move, "teamId")),
        move=move,
        symbol=symbol_text,
        move_x=_coerce_optional_int(raw_move.get("moveX")),
        move_y=_coerce_optional_int(raw_move.get("moveY")),
    )


def parse_game_details_payload(payload: Mapping[str, Any]) -> RemoteGameDetails:
    raw_game = payload.get("game")
    decoded = _decode_nested_json(raw_game)
    if not isinstance(decoded, dict):
        raise P2PApiError("Expected 'game' to decode to a JSON object.", payload)

    return RemoteGameDetails(
        game_id=_coerce_int(_require_value(decoded, "gameId")),
        game_type=str(_require_value(decoded, "gameType", "gametype")),
        move_count=_coerce_int(_require_value(decoded, "moves")),
        board_size=_coerce_int(_require_value(decoded, "boardSize", "boardsize")),
        target=_coerce_int(_require_value(decoded, "target")),
        team1_id=_coerce_int(_require_value(decoded, "team1Id", "team1id")),
        team1_name=str(_require_value(decoded, "team1Name", "team1name")),
        team2_id=_coerce_int(_require_value(decoded, "team2Id", "team2id")),
        team2_name=str(_require_value(decoded, "team2Name", "team2name")),
        seconds_per_move=_coerce_optional_int(
            _find_value(decoded, "secondsPerMove", "secondspermove")
        ),
        status=str(_require_value(decoded, "status")),
        winner_team_id=_coerce_optional_int(
            _find_value(decoded, "winnerTeamId", "winnerteamid")
        ),
        turn_team_id=_coerce_optional_int(_find_value(decoded, "turnTeamId", "turnteamid")),
    )


def parse_board_map_payload(payload: Mapping[str, Any]) -> dict[tuple[int, int], str]:
    raw_output = payload.get("output")
    if raw_output is None:
        return {}
    decoded = _decode_nested_json(raw_output)
    if not isinstance(decoded, dict):
        raise P2PApiError("Expected 'output' to decode to a JSON object.", payload)

    board: dict[tuple[int, int], str] = {}
    for key, value in decoded.items():
        move = parse_move_text(str(key))
        symbol = str(value).upper()
        if symbol not in {"X", "O"}:
            raise P2PApiError(f"Unexpected board symbol {value!r} at {key!r}.")
        board[move] = symbol
    return board


def parse_move_text(value: str) -> tuple[int, int]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        raise ValueError(f"Expected move in 'row,col' format, got {value!r}.")
    return int(parts[0]), int(parts[1])


def infer_symbol_by_team(
    details: RemoteGameDetails,
    recent_moves: list[RemoteMove] | None = None,
) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for move in recent_moves or []:
        if move.symbol in {"X", "O"}:
            mapping[move.team_id] = move.symbol

    if len(mapping) == 1:
        known_team_id, known_symbol = next(iter(mapping.items()))
        other_team_id = details.team2_id if known_team_id == details.team1_id else details.team1_id
        mapping[other_team_id] = "O" if known_symbol == "X" else "X"
        return mapping

    if len(mapping) == 2:
        return mapping

    # The PDF's example payloads consistently show team1 as O and team2 as X.
    return {details.team1_id: "O", details.team2_id: "X"}


def build_game_state(
    details: RemoteGameDetails,
    board_map: Mapping[tuple[int, int], str],
    symbol_by_team: Mapping[int, str],
) -> GameState:
    board = [EMPTY] * (details.board_size * details.board_size)
    for (row, col), symbol in board_map.items():
        if not (0 <= row < details.board_size and 0 <= col < details.board_size):
            raise ValueError(f"Board cell {(row, col)} is outside the board.")
        idx = row * details.board_size + col
        board[idx] = _symbol_to_local(symbol)

    winner: Symbol | None = None
    if details.winner_team_id is not None and details.winner_team_id in symbol_by_team:
        winner = _symbol_to_local(symbol_by_team[details.winner_team_id])

    if winner is not None and details.turn_team_id is None:
        current_player = winner
    else:
        current_player = _infer_current_player(details, board_map, symbol_by_team)
    return GameState(
        n=details.board_size,
        m=details.target,
        board=tuple(board),
        current_player=current_player,
        last_move=None,
        winner=winner,
    )


def _infer_current_player(
    details: RemoteGameDetails,
    board_map: Mapping[tuple[int, int], str],
    symbol_by_team: Mapping[int, str],
) -> Symbol:
    if details.turn_team_id is not None and details.turn_team_id in symbol_by_team:
        return _symbol_to_local(symbol_by_team[details.turn_team_id])

    x_count = sum(1 for symbol in board_map.values() if symbol == "X")
    o_count = sum(1 for symbol in board_map.values() if symbol == "O")
    if o_count == x_count:
        starter_symbol = symbol_by_team.get(details.team1_id, "O")
        return _symbol_to_local(starter_symbol)
    if o_count == x_count + 1:
        non_starter_symbol = symbol_by_team.get(details.team2_id, "X")
        return _symbol_to_local(non_starter_symbol)
    raise ValueError("Could not infer the current player from board counts.")


def _symbol_to_local(symbol: str) -> Symbol:
    normalized = symbol.upper()
    if normalized == "X":
        return X
    if normalized == "O":
        return O
    raise ValueError(f"Unsupported symbol: {symbol!r}")


def _decode_nested_json(value: Any) -> Any:
    current = value
    for _ in range(3):
        if not isinstance(current, str):
            return current
        stripped = current.strip()
        if not stripped:
            return stripped
        if stripped[0] not in "[{":
            return current
        try:
            current = json.loads(stripped)
        except json.JSONDecodeError:
            return current
    return current


def _stringify_mapping(params: Mapping[str, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in params.items()}


def _as_int_list(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[int] = []
        for item in value:
            if isinstance(item, Mapping):
                for key in item.keys():
                    out.append(_coerce_int(key))
            else:
                out.append(_coerce_int(item))
        return out
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        return [_coerce_int(part) for part in stripped.split(",")]
    raise P2PApiError(f"Expected list-like value, got {type(value).__name__}.")


def _should_retry_request(
    method: str,
    *,
    curl_exit_code: int | None,
    http_status_code: int | None,
    attempt: int,
    max_attempts: int,
) -> bool:
    if method != "GET" or attempt >= max_attempts:
        return False
    if curl_exit_code is None and http_status_code is None:
        return True
    if curl_exit_code is not None:
        return curl_exit_code in CURL_TRANSIENT_EXIT_CODES
    if http_status_code is not None:
        return http_status_code in HTTP_TRANSIENT_STATUS_CODES
    return False


def _require_int(payload: Mapping[str, Any], key: str) -> int:
    return _coerce_int(_require_value(payload, key))


def _coerce_int(value: Any) -> int:
    return int(str(value))


def _coerce_optional_int(value: Any) -> int | None:
    if value in (None, "", "null", "None"):
        return None
    return _coerce_int(value)


def _require_value(mapping: Mapping[str, Any], *keys: str) -> Any:
    found = _find_value(mapping, *keys)
    if found is None:
        joined = ", ".join(keys)
        raise P2PApiError(f"Missing required key: {joined}")
    return found


def _find_value(mapping: Mapping[str, Any], *keys: str) -> Any:
    lowered = {str(key).lower(): value for key, value in mapping.items()}
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
        lowered_key = key.lower()
        if lowered_key in lowered and lowered[lowered_key] is not None:
            return lowered[lowered_key]
    return None
