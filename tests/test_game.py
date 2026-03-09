import unittest

from ttt.agent import MinimaxAgent
from ttt.game import O, X, GameState


class GameStateTests(unittest.TestCase):
    def test_row_win_detection(self) -> None:
        state = GameState.new(n=3, m=3)
        state = state.apply_move((0, 0))  # X
        state = state.apply_move((1, 0))  # O
        state = state.apply_move((0, 1))  # X
        state = state.apply_move((1, 1))  # O
        state = state.apply_move((0, 2))  # X wins
        self.assertEqual(state.winner, X)
        self.assertTrue(state.is_terminal())

    def test_diagonal_win_detection(self) -> None:
        state = GameState.new(n=4, m=3)
        state = state.apply_move((0, 0))  # X
        state = state.apply_move((0, 1))  # O
        state = state.apply_move((1, 1))  # X
        state = state.apply_move((1, 0))  # O
        state = state.apply_move((2, 2))  # X wins with 3 diagonal
        self.assertEqual(state.winner, X)


class AgentTests(unittest.TestCase):
    def test_agent_takes_immediate_win(self) -> None:
        # Board:
        # X X .
        # O O .
        # . . .
        # X to move should play (0, 2) and win.
        state = GameState.new(n=3, m=3)
        state = state.apply_move((0, 0))  # X
        state = state.apply_move((1, 0))  # O
        state = state.apply_move((0, 1))  # X
        state = state.apply_move((1, 1))  # O
        self.assertEqual(state.current_player, X)

        agent = MinimaxAgent(max_depth=3, time_limit_s=0.5)
        move = agent.choose_move(state)
        self.assertEqual(move, (0, 2))

    def test_agent_blocks_threat(self) -> None:
        # Board:
        # O O .
        # X . .
        # X . .
        # O to move can win at (0, 2), so X must block if X turn.
        state = GameState.new(n=3, m=3, first_player=O)
        state = state.apply_move((0, 0))  # O
        state = state.apply_move((1, 0))  # X
        state = state.apply_move((0, 1))  # O
        state = state.apply_move((2, 0))  # X
        self.assertEqual(state.current_player, O)

        o_agent = MinimaxAgent(max_depth=3, time_limit_s=0.5)
        move = o_agent.choose_move(state)
        self.assertEqual(move, (0, 2))


if __name__ == "__main__":
    unittest.main()
