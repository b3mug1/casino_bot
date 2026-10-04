import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database import CasinoDatabase, InsufficientBalance


class CasinoDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = CasinoDatabase(
            str(Path(self.temp_dir.name) / "casino.db"), starting_balance=100
        )
        self.database.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_new_user_receives_starting_balance(self) -> None:
        self.assertEqual(self.database.get_balance(42), 100)

    def test_winning_round_adds_stake(self) -> None:
        with patch("database.secrets.randbelow", return_value=0):
            result = self.database.play_round(42, 25, "орел")

        self.assertTrue(result.won)
        self.assertEqual(result.outcome, "орел")
        self.assertEqual(result.balance, 125)
        self.assertEqual(self.database.get_balance(42), 125)

    def test_losing_round_deducts_stake(self) -> None:
        with patch("database.secrets.randbelow", return_value=1):
            result = self.database.play_round(42, 25, "орел")

        self.assertFalse(result.won)
        self.assertEqual(result.outcome, "решка")
        self.assertEqual(result.balance, 75)

    def test_zero_stake_is_rejected_without_changing_balance(self) -> None:
        with self.assertRaises(ValueError):
            self.database.play_round(42, 0, "орел")
        self.assertEqual(self.database.get_balance(42), 100)

    def test_negative_stake_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.database.play_round(42, -10, "орел")

    def test_stake_above_balance_is_rejected_without_changing_balance(self) -> None:
        with self.assertRaises(InsufficientBalance) as error:
            self.database.play_round(42, 101, "орел")

        self.assertEqual(error.exception.balance, 100)
        self.assertEqual(self.database.get_balance(42), 100)

    def test_invalid_choice_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.database.play_round(42, 10, "invalid")

    def test_winning_balance_cannot_overflow_sqlite_integer(self) -> None:
        database = CasinoDatabase(
            str(Path(self.temp_dir.name) / "large.db"),
            starting_balance=CasinoDatabase.MAX_BALANCE,
        )
        database.initialize()

        with self.assertRaises(ValueError):
            database.play_round(42, 1, "орел")

        self.assertEqual(database.get_balance(42), CasinoDatabase.MAX_BALANCE)


if __name__ == "__main__":
    unittest.main()
