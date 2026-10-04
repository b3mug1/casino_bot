import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class RoundResult:
    outcome: str
    won: bool
    balance: int


class InsufficientBalance(Exception):
    def __init__(self, balance: int) -> None:
        self.balance = balance
        super().__init__(f"Insufficient balance: {balance}")


class CasinoDatabase:
    MAX_BALANCE = 9_223_372_036_854_775_807

    def __init__(self, path: str, starting_balance: int = 1_000) -> None:
        if starting_balance < 0:
            raise ValueError("Starting balance cannot be negative")
        self.path = Path(path)
        self.starting_balance = starting_balance

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER NOT NULL CHECK (balance >= 0)
                )
                """
            )

    def get_balance(self, user_id: int) -> int:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)",
                (user_id, self.starting_balance),
            )
            row = connection.execute(
                "SELECT balance FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
        if row is None:
            raise sqlite3.DatabaseError("Could not load user balance")
        return int(row["balance"])

    def play_round(self, user_id: int, amount: int, choice: str) -> RoundResult:
        if amount <= 0:
            raise ValueError("Ставка должна быть больше нуля.")
        if choice not in {"орел", "решка"}:
            raise ValueError("Выберите «орел» или «решка».")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)",
                (user_id, self.starting_balance),
            )
            row = connection.execute(
                "SELECT balance FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row is None:
                raise sqlite3.DatabaseError("Could not load user balance")

            balance = int(row["balance"])
            if amount > balance:
                raise InsufficientBalance(balance)
            if amount > self.MAX_BALANCE - balance:
                raise ValueError("Эта ставка превысит допустимый размер баланса.")

            outcome = "орел" if secrets.randbelow(2) == 0 else "решка"
            won = outcome == choice
            new_balance = balance + amount if won else balance - amount
            connection.execute(
                "UPDATE users SET balance = ? WHERE user_id = ?",
                (new_balance, user_id),
            )

        return RoundResult(outcome=outcome, won=won, balance=new_balance)
