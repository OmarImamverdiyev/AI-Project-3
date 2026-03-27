import unittest

from ttt.game import O, X
from ttt.p2p import (
    RemoteGameDetails,
    RemoteMove,
    _as_int_list,
    build_game_state,
    infer_symbol_by_team,
    parse_board_map_payload,
    parse_game_details_payload,
)


class P2PParsingTests(unittest.TestCase):
    def test_parse_game_details_from_nested_json_string(self) -> None:
        payload = {
            "game": (
                "{\"gameId\":\"4670\",\"gameType\":\"TTT\",\"moves\":\"1\","
                "\"boardsize\":\"12\",\"target\":\"6\",\"team1id\":\"1041\","
                "\"team1Name\":\"Team 1041\",\"team2id\":\"1042\","
                "\"team2Name\":\"Team 1042\",\"secondspermove\":\"600\","
                "\"status\":\"0\",\"winnerteamid\":null,\"turnteamid\":\"1042\"}"
            ),
            "code": "OK",
        }

        details = parse_game_details_payload(payload)

        self.assertEqual(details.game_id, 4670)
        self.assertEqual(details.board_size, 12)
        self.assertEqual(details.target, 6)
        self.assertEqual(details.team1_id, 1041)
        self.assertEqual(details.team2_id, 1042)
        self.assertEqual(details.turn_team_id, 1042)
        self.assertIsNone(details.winner_team_id)

    def test_parse_board_map_from_nested_json_string(self) -> None:
        payload = {
            "output": "{\"11,15\":\"O\",\"11,16\":\"X\",\"11,17\":\"O\"}",
            "code": "OK",
        }

        board = parse_board_map_payload(payload)

        self.assertEqual(board[(11, 15)], "O")
        self.assertEqual(board[(11, 16)], "X")
        self.assertEqual(board[(11, 17)], "O")

    def test_parse_board_map_from_null_output(self) -> None:
        payload = {"output": None, "code": "OK"}

        board = parse_board_map_payload(payload)

        self.assertEqual(board, {})

    def test_parse_int_list_from_game_objects(self) -> None:
        values = [{"5482": "1484:1481:O"}, {"5483": "1484:1500:X"}]

        parsed = _as_int_list(values)

        self.assertEqual(parsed, [5482, 5483])


class P2PGameStateTests(unittest.TestCase):
    def test_infer_symbols_from_recent_move(self) -> None:
        details = RemoteGameDetails(
            game_id=1310,
            game_type="TTT",
            move_count=4,
            board_size=20,
            target=10,
            team1_id=1041,
            team1_name="Team 1041",
            team2_id=1082,
            team2_name="Team 1082",
            seconds_per_move=600,
            status="0",
            winner_team_id=None,
            turn_team_id=1041,
        )
        recent_moves = [
            RemoteMove(
                move_id=6331,
                game_id=1310,
                team_id=1082,
                move=(10, 3),
                symbol="X",
                move_x=10,
                move_y=3,
            )
        ]

        mapping = infer_symbol_by_team(details, recent_moves)

        self.assertEqual(mapping, {1041: "O", 1082: "X"})

    def test_build_game_state_sets_board_and_turn(self) -> None:
        details = RemoteGameDetails(
            game_id=1310,
            game_type="TTT",
            move_count=4,
            board_size=20,
            target=10,
            team1_id=1041,
            team1_name="Team 1041",
            team2_id=1082,
            team2_name="Team 1082",
            seconds_per_move=600,
            status="0",
            winner_team_id=None,
            turn_team_id=1041,
        )
        board_map = {
            (11, 17): "O",
            (11, 9): "X",
            (10, 2): "O",
            (10, 3): "X",
        }
        symbol_by_team = {1041: "O", 1082: "X"}

        state = build_game_state(details, board_map, symbol_by_team)

        self.assertEqual(state.at(11, 17), O)
        self.assertEqual(state.at(11, 9), X)
        self.assertEqual(state.current_player, O)
        self.assertEqual(len(state.legal_moves()), details.board_size * details.board_size - 4)


if __name__ == "__main__":
    unittest.main()
