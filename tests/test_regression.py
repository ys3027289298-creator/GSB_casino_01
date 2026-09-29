import unittest

import core


class TestIdempotency(unittest.TestCase):
    def test_exchange_different_amount_still_rejected(self):
        state = core.new_game()
        self.assertTrue(core.exchange(state, "P1", 100))
        self.assertFalse(core.exchange(state, "P1", 50))
        self.assertEqual(state["chips"]["P1"], 100)

    def test_bet_twice_rejected_without_double_charge(self):
        state = core.new_game()
        core.exchange(state, "P1", 100)
        self.assertTrue(core.bet(state, "P1", 30))
        self.assertFalse(core.bet(state, "P1", 30))
        self.assertEqual(state["chips"]["P1"], 70)
        self.assertEqual(state["bets"]["P1"], 30)

    def test_cancel_idempotent(self):
        state = core.new_game()
        core.exchange(state, "P1", 100)
        core.bet(state, "P1", 50)
        self.assertTrue(core.cancel_bet(state, "P1"))
        self.assertFalse(core.cancel_bet(state, "P1"))
        self.assertEqual(state["chips"]["P1"], 100)
        self.assertNotIn("P1", state["bets"])

    def test_settle_idempotent(self):
        state = core.new_game()
        core.exchange(state, "P1", 100)
        core.bet(state, "P1", 50)
        self.assertTrue(core.settle(state, "P1"))
        self.assertFalse(core.settle(state, "P1"))
        self.assertEqual(state["round_id"], 1)

    def test_cheat_idempotent_per_round(self):
        state = core.new_game()
        self.assertEqual(core.cheat(state), 90)
        self.assertFalse(core.cheat(state))
        self.assertEqual(state["credit"], 90)

    def test_cheat_allowed_again_next_round(self):
        state = core.new_game()
        core.cheat(state)
        core.exchange(state, "P1", 10)
        core.bet(state, "P1", 1)
        core.settle(state, "P1")
        self.assertEqual(state["round_id"], 1)
        self.assertEqual(core.cheat(state), 80)

    def test_payout_success_then_repeat_fails_cleanly(self):
        state = core.new_game()
        core.exchange(state, "P1", 100)
        self.assertTrue(core.payout(state, "P1", 40))
        self.assertFalse(core.payout(state, "P1", 70))
        self.assertEqual(state["chips"]["P1"], 60)


class TestBoundariesAndValidation(unittest.TestCase):
    def test_bet_exact_balance_allowed(self):
        state = core.new_game()
        core.exchange(state, "P1", 100)
        self.assertTrue(core.bet(state, "P1", 100))
        self.assertEqual(state["chips"]["P1"], 0)

    def test_bet_over_limit_rejected_unchanged(self):
        state = core.new_game()
        core.exchange(state, "P1", 100)
        self.assertFalse(core.bet(state, "P1", 101))
        self.assertEqual(state["chips"]["P1"], 100)
        self.assertNotIn("P1", state["bets"])

    def test_invalid_amounts_rejected(self):
        state = core.new_game()
        for bad in (0, -1, 1.5, "10", True, None):
            self.assertFalse(core.exchange(core.new_game(), "Px", bad))
            self.assertFalse(core.bet(state, "P1", bad))
            self.assertFalse(core.payout(state, "P1", bad))
        self.assertFalse(core.exchange(state, "", 10))
        self.assertFalse(core.exchange(state, None, 10))

    def test_unknown_player_operations(self):
        state = core.new_game()
        self.assertFalse(core.bet(state, "ghost", 10))
        self.assertFalse(core.cancel_bet(state, "ghost"))
        self.assertFalse(core.settle(state, "ghost"))
        self.assertFalse(core.payout(state, "ghost", 10))

    def test_odds_boundaries(self):
        state = core.new_game()
        self.assertEqual(core.odds(state, 100, 2), 200)
        self.assertEqual(core.odds(state, 0, 3), 0)
        for bad_base, bad_rate in ((-1, 2), (10, 0), ("x", 2), (10, "y")):
            with self.assertRaises(ValueError):
                core.odds(state, bad_base, bad_rate)

    def test_house_fault_keeps_bet_and_round(self):
        state = core.new_game()
        core.exchange(state, "P1", 100)
        core.bet(state, "P1", 40)
        state["house_fault"] = True
        self.assertFalse(core.settle(state, "P1"))
        self.assertEqual(state["bets"]["P1"], 40)
        self.assertEqual(state["chips"]["P1"], 60)
        self.assertEqual(state["round_id"], 0)


class TestPersistence(unittest.TestCase):
    def test_save_load_roundtrip_stable_and_round_preserved(self):
        state = core.new_game()
        state["round_id"] = 7
        core.exchange(state, "P1", 50)
        core.bet(state, "P1", 20)
        loaded = core.load_state(core.save_state(state))
        self.assertEqual(loaded["round_id"], 7)
        self.assertEqual(loaded["chips"], {"P1": 30})
        self.assertEqual(loaded["bets"], {"P1": 20})
        loaded_again = core.load_state(core.save_state(loaded))
        self.assertEqual(loaded_again["round_id"], 7)

    def test_load_empty_or_malformed(self):
        for bad in ("", "   ", "not json", "[]", "{}",
                    '{"chips": {}, "bets": {}, "credit": 1, "round_id": "x"}'):
            with self.assertRaises(ValueError):
                core.load_state(bad)


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.state = core.new_game()

    def cmd(self, line):
        return core.run_command(self.state, line)

    def test_illegal_and_empty_commands(self):
        self.assertTrue(self.cmd("nonsense").startswith("error"))
        self.assertTrue(self.cmd("   ").startswith("error"))
        self.assertTrue(self.cmd("exchange P1").startswith("error"))
        self.assertTrue(self.cmd("exchange P1 abc").startswith("error"))
        self.assertTrue(self.cmd("odds 100 0").startswith("error"))

    def test_command_idempotency_script(self):
        self.assertEqual(self.cmd("exchange P1 100"), "ok")
        self.assertNotEqual(self.cmd("exchange P1 100"), "ok")
        self.assertEqual(self.cmd("odds 100 2"), "ok 200")
        self.assertNotEqual(self.cmd("bet P1 200"), "ok")
        self.assertEqual(self.cmd("bet P1 100"), "ok")
        self.assertNotEqual(self.cmd("bet P1 1"), "ok")
        self.assertEqual(self.cmd("cheat"), "ok 90")
        self.assertNotEqual(self.cmd("cheat"), "ok 80")
        self.assertEqual(self.cmd("cancel P1"), "ok")
        self.assertNotEqual(self.cmd("cancel P1"), "ok")
        self.assertEqual(self.cmd("payout P1 200"), "error: command rejected")
        self.assertEqual(self.cmd("payout P1 50"), "ok")


if __name__ == "__main__":
    unittest.main()
