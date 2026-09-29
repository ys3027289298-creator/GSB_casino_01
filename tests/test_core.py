import unittest

import core


class TestCore(unittest.TestCase):
    def test_01_no_duplicate_exchange(self):
        state = core.new_game()
        self.assertTrue(core.exchange(state, "P1", 100))
        self.assertFalse(core.exchange(state, "P1", 100))

    def test_02_odds_direction(self):
        state = core.new_game()
        self.assertEqual(core.odds(state, 100, 2), 200)

    def test_03_bet_limit(self):
        state = core.new_game()
        core.exchange(state, "P1", 100)
        result = core.bet(state, "P1", 200)
        self.assertFalse(result)

    def test_04_cancel_bet_refunds(self):
        state = core.new_game()
        core.exchange(state, "P1", 100)
        core.bet(state, "P1", 50)
        core.cancel_bet(state, "P1")
        self.assertEqual(state["chips"]["P1"], 100)

    def test_05_no_settle_on_house_fault(self):
        state = core.new_game()
        state["house_fault"] = True
        result = core.settle(state, "P1")
        self.assertFalse(result)

    def test_06_cheat_once(self):
        state = core.new_game()
        core.cheat(state)
        self.assertEqual(state["credit"], 90)

    def test_07_payout_failure_no_cost(self):
        state = core.new_game()
        core.exchange(state, "P1", 10)
        result = core.payout(state, "P1", 20)
        self.assertFalse(result)
        self.assertEqual(state["chips"]["P1"], 10)

    def test_08_load_preserves_round(self):
        state = core.new_game()
        state["round_id"] = 5
        loaded = core.load_state(core.save_state(state))
        self.assertEqual(loaded["round_id"], 5)


if __name__ == "__main__":
    unittest.main()
