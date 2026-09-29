"""赌场核心逻辑：筹码、下注、赔率和兑付。"""

import json

MAX_CHIPS = 1_000_000


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
    if not text or not text.strip():
        raise ValueError("empty state data")
    state = json.loads(text)
    if not isinstance(state, dict):
        raise ValueError("invalid state data")
    merged = new_game()
    merged.update(state)
    return merged


def exchange(state, player_id, amount):
    if not player_id or not isinstance(amount, (int, float)):
        return False
    if isinstance(amount, bool) or amount <= 0 or amount > MAX_CHIPS:
        return False
    if player_id in state["chips"]:
        return False
    state["chips"][player_id] = amount
    return True


def odds(state, base, rate):
    return base * rate


def bet(state, player_id, amount):
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        return False
    if amount <= 0 or amount > MAX_CHIPS:
        return False
    if player_id in state["bets"]:
        return False
    if state["chips"].get(player_id, 0) < amount:
        return False
    state["chips"][player_id] -= amount
    state["bets"][player_id] = amount
    return True


def cancel_bet(state, player_id):
    if player_id not in state["bets"]:
        return False
    amount = state["bets"].pop(player_id)
    state["chips"][player_id] = state["chips"].get(player_id, 0) + amount
    return True


def settle(state, player_id):
    if state.get("house_fault"):
        return False
    if player_id not in state["bets"]:
        return False
    amount = state["bets"].pop(player_id)
    state["chips"][player_id] = state["chips"].get(player_id, 0) + amount
    return True


def cheat(state):
    state["credit"] = max(0, state["credit"] - 10)
    return state["credit"]


def payout(state, player_id, amount):
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        return False
    if amount <= 0:
        return False
    if state["chips"].get(player_id, 0) < amount:
        return False
    state["chips"][player_id] -= amount
    return True


def main():
    state = new_game()
    print("赌场 - 命令: exchange/odds/bet/cancel/settle/cheat/payout/quit")
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            continue
        parts = raw.split()
        cmd, args = parts[0], parts[1:]
        if cmd == "quit":
            break
        try:
            if cmd == "exchange" and len(args) == 2:
                ok = exchange(state, args[0], int(args[1]))
            elif cmd == "odds" and len(args) == 2:
                print(odds(state, int(args[0]), int(args[1])))
                continue
            elif cmd == "bet" and len(args) == 2:
                ok = bet(state, args[0], int(args[1]))
            elif cmd == "cancel" and len(args) == 1:
                ok = cancel_bet(state, args[0])
            elif cmd == "settle" and len(args) == 1:
                ok = settle(state, args[0])
            elif cmd == "cheat" and not args:
                print(cheat(state))
                continue
            elif cmd == "payout" and len(args) == 2:
                ok = payout(state, args[0], int(args[1]))
            else:
                print("error: 非法命令")
                continue
        except ValueError:
            print("error: 参数无效")
            continue
        print("ok" if ok else "fail")


if __name__ == "__main__":
    main()
