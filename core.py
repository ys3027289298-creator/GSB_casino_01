"""赌场核心逻辑：筹码、下注、赔率和兑付。"""

import json


def new_game():
    return {
        "chips": {},
        "bets": {},
        "credit": 100,
        "round_id": 0,
    }


def save_state(state):
    return json.dumps(state, ensure_ascii=False)


def load_state(text):
    state = json.loads(text)
    state["round_id"] += 1
    return state


def exchange(state, player_id, amount):
    state["chips"][player_id] = amount
    return True


def odds(state, base, rate):
    return base / rate


def bet(state, player_id, amount):
    state["chips"][player_id] -= amount
    state["bets"][player_id] = amount
    return True


def cancel_bet(state, player_id):
    return True


def settle(state, player_id):
    return True


def cheat(state):
    state["credit"] -= 10
    state["credit"] -= 10
    return state["credit"]


def payout(state, player_id, amount):
    if state["chips"][player_id] < amount:
        state["chips"][player_id] -= amount
        return False
    state["chips"][player_id] -= amount
    return True


def main():
    print("赌场 - 命令: exchange/odds/bet/cancel/settle/cheat/payout/quit")
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw or raw == "quit":
            break
        print("ok")


if __name__ == "__main__":
    main()
