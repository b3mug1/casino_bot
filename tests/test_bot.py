import unittest

from bot import parse_bet


class ParseBetTests(unittest.TestCase):
    def test_accepts_russian_choice(self) -> None:
        self.assertEqual(parse_bet("100 орёл"), (100, "орел"))

    def test_accepts_english_choice_case_insensitively(self) -> None:
        self.assertEqual(parse_bet("25 HEADS"), (25, "орел"))

    def test_rejects_missing_or_extra_arguments(self) -> None:
        self.assertIsNone(parse_bet(None))
        self.assertIsNone(parse_bet("100"))
        self.assertIsNone(parse_bet("100 орел extra"))

    def test_rejects_non_integer_or_out_of_range_stakes(self) -> None:
        self.assertIsNone(parse_bet("0.5 орел"))
        self.assertIsNone(parse_bet("-10 орел"))
        self.assertIsNone(parse_bet("9223372036854775808 орел"))

    def test_rejects_unknown_choice(self) -> None:
        self.assertIsNone(parse_bet("100 камень"))


if __name__ == "__main__":
    unittest.main()
