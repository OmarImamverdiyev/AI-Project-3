import os
import tempfile
import unittest
from pathlib import Path

from ttt.env_utils import env_float, env_int, env_str, load_dotenv, upsert_dotenv


class DotenvTests(unittest.TestCase):
    def test_load_dotenv_parses_values_and_comments(self) -> None:
        original_user = os.environ.get("AIP2P_USER_ID")
        original_depth = os.environ.get("AIP2P_DEPTH")
        try:
            os.environ.pop("AIP2P_USER_ID", None)
            os.environ.pop("AIP2P_DEPTH", None)

            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / ".env"
                path.write_text(
                    "# comment\n"
                    "AIP2P_USER_ID=3733\n"
                    "AIP2P_DEPTH=\"4\"  # inline comment\n",
                    encoding="utf-8",
                )

                loaded = load_dotenv(path)

            self.assertEqual(loaded["AIP2P_USER_ID"], "3733")
            self.assertEqual(loaded["AIP2P_DEPTH"], "4")
            self.assertEqual(env_str("AIP2P_USER_ID"), "3733")
            self.assertEqual(env_int("AIP2P_DEPTH"), 4)
        finally:
            if original_user is None:
                os.environ.pop("AIP2P_USER_ID", None)
            else:
                os.environ["AIP2P_USER_ID"] = original_user

            if original_depth is None:
                os.environ.pop("AIP2P_DEPTH", None)
            else:
                os.environ["AIP2P_DEPTH"] = original_depth

    def test_load_dotenv_does_not_override_existing_values_by_default(self) -> None:
        original_poll = os.environ.get("AIP2P_POLL_SECONDS")
        try:
            os.environ["AIP2P_POLL_SECONDS"] = "9"

            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / ".env"
                path.write_text("AIP2P_POLL_SECONDS=5\n", encoding="utf-8")
                load_dotenv(path)

            self.assertEqual(env_float("AIP2P_POLL_SECONDS"), 9.0)
        finally:
            if original_poll is None:
                os.environ.pop("AIP2P_POLL_SECONDS", None)
            else:
                os.environ["AIP2P_POLL_SECONDS"] = original_poll

    def test_upsert_dotenv_updates_existing_keys_and_appends_new_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".env"
            path.write_text(
                "AIP2P_USER_ID=3733\n"
                "AIP2P_GAME_ID=\n",
                encoding="utf-8",
            )

            upsert_dotenv(
                path,
                {
                    "AIP2P_GAME_ID": 5500,
                    "AIP2P_TEAM_ID": 1484,
                },
            )

            text = path.read_text(encoding="utf-8")

        self.assertIn("AIP2P_USER_ID=3733\n", text)
        self.assertIn("AIP2P_GAME_ID=5500\n", text)
        self.assertIn("AIP2P_TEAM_ID=1484\n", text)


if __name__ == "__main__":
    unittest.main()
