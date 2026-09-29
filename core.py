"""赌场核心逻辑：筹码、下注、赔率和兑付。

所有写操作均幂等：重复的合法请求不会再次改变状态，而是返回 False。
仅使用标准库；状态 JSON 的既有键名保持不变。
"""

import json


CREDIT_START = 100
CHEAT_PENALTY = 10


def new_game():
    return {
        "chips": {},
        "bets": {},
        "credit": CREDIT_START,
        "round_id": 0,
        "cheated_rounds": [],
    }


def save_state(state):
    return json.dumps(state, ensure_ascii=False)


def load_state(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty state data")
    try:
        state = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid state data") from exc
    if not isinstance(state, dict):
        raise ValueError("invalid state data")
    for key in ("chips", "bets"):
        if not isinstance(state.get(key), dict):
            raise ValueError("invalid state data")
    if not isinstance(state.get("credit"), int) or isinstance(state.get("credit"), bool):
        raise ValueError("invalid state data")
    if not isinstance(state.get("round_id"), int) or isinstance(state.get("round_id"), bool):
        raise ValueError("invalid state data")
    if not isinstance(state.get("cheated_rounds"), list):
        state["cheated_rounds"] = []
    # 读档只恢复局号，绝不自增，避免局号重复/跳号。
    return state


def _valid_state(state):
    return (
        isinstance(state, dict)
        and isinstance(state.get("chips"), dict)
        and isinstance(state.get("bets"), dict)
        and isinstance(state.get("credit"), int)
        and isinstance(state.get("round_id"), int)
        and isinstance(state.get("cheated_rounds"), list)
    )


def _valid_player(player_id):
    return isinstance(player_id, str) and player_id != ""


def _valid_amount(amount):
    # 容量/空数据检查：必须是正整数，拒绝布尔、零、负数、浮点和字符串。
    return isinstance(amount, int) and not isinstance(amount, bool) and amount > 0


def _advance_round(state):
    state["round_id"] += 1


def exchange(state, player_id, amount):
    """同一玩家只能兑换一次；重复兑换（无论金额）返回 False，不覆盖余额。"""
    if not _valid_state(state) or not _valid_player(player_id) or not _valid_amount(amount):
        return False
    if player_id in state["chips"]:
        return False
    state["chips"][player_id] = amount
    return True


def odds(state, base, rate):
    """赔率 = 本金 × 赔率乘数（纯计算，不修改状态）。"""
    if not _valid_state(state):
        raise ValueError("invalid state")
    if isinstance(base, bool) or isinstance(rate, bool):
        raise ValueError("invalid odds arguments")
    if not isinstance(base, (int, float)) or not isinstance(rate, (int, float)):
        raise ValueError("invalid odds arguments")
    if base < 0 or rate <= 0:
        raise ValueError("invalid odds arguments")
    return base * rate


def bet(state, player_id, amount):
    """下注：金额必须为正整数且不超过筹码余额；每名玩家同时只保留一笔有效下注。"""
    if not _valid_state(state) or not _valid_player(player_id) or not _valid_amount(amount):
        return False
    if player_id not in state["chips"]:
        return False
    if player_id in state["bets"]:
        return False
    # 容量临界：余额恰好等于下注额时允许（等额下注合法）。
    if state["chips"][player_id] < amount:
        return False
    state["chips"][player_id] -= amount
    state["bets"][player_id] = amount
    return True


def cancel_bet(state, player_id):
    """取消下注并退还筹码；无有效下注时返回 False，重复取消不产生副作用。"""
    if not _valid_state(state) or not _valid_player(player_id):
        return False
    amount = state["bets"].pop(player_id, None)
    if amount is None:
        return False
    state["chips"][player_id] = state["chips"].get(player_id, 0) + amount
    return True


def settle(state, player_id):
    """结算一笔有效下注；庄家故障时拒绝结算且不改状态，重复结算返回 False。"""
    if not _valid_state(state) or not _valid_player(player_id):
        return False
    if state.get("house_fault"):
        return False
    if player_id not in state["bets"]:
        return False
    del state["bets"][player_id]
    if not state["bets"]:
        _advance_round(state)
    return True


def cheat(state):
    """作弊每局只扣一次信誉；同一局重复上报返回 False，不重复扣分。"""
    if not _valid_state(state):
        return False
    round_id = state["round_id"]
    if round_id in state["cheated_rounds"]:
        return False
    state["credit"] -= CHEAT_PENALTY
    state["cheated_rounds"].append(round_id)
    return state["credit"]


def payout(state, player_id, amount):
    """兑付：余额不足或参数非法时返回 False 且不扣筹码；成功才扣款。"""
    if not _valid_state(state) or not _valid_player(player_id) or not _valid_amount(amount):
        return False
    balance = state["chips"].get(player_id)
    if balance is None or balance < amount:
        return False
    state["chips"][player_id] = balance - amount
    return True


def _parse_number(text):
    try:
        return int(text)
    except (TypeError, ValueError):
        return float(text)


def run_command(state, raw):
    """解析并执行一行命令，返回要打印的结果字符串。"""
    if not isinstance(raw, str):
        return "error: invalid command"
    line = raw.strip()
    if not line:
        return "error: empty command"
    parts = line.split()
    cmd, args = parts[0], parts[1:]
    try:
        if cmd == "exchange":
            if len(args) != 2:
                return "error: usage: exchange <player> <amount>"
            ok = exchange(state, args[0], _parse_number(args[1]))
        elif cmd == "odds":
            if len(args) != 2:
                return "error: usage: odds <base> <rate>"
            return "ok %s" % odds(state, _parse_number(args[0]), _parse_number(args[1]))
        elif cmd == "bet":
            if len(args) != 2:
                return "error: usage: bet <player> <amount>"
            ok = bet(state, args[0], _parse_number(args[1]))
        elif cmd == "cancel":
            if len(args) != 1:
                return "error: usage: cancel <player>"
            ok = cancel_bet(state, args[0])
        elif cmd == "settle":
            if len(args) != 1:
                return "error: usage: settle <player>"
            ok = settle(state, args[0])
        elif cmd == "cheat":
            if args:
                return "error: usage: cheat"
            result = cheat(state)
            if result is False:
                return "error: cheat already recorded this round"
            return "ok %s" % result
        elif cmd == "payout":
            if len(args) != 2:
                return "error: usage: payout <player> <amount>"
            ok = payout(state, args[0], _parse_number(args[1]))
        else:
            return "error: unknown command"
    except (ValueError, TypeError):
        return "error: invalid arguments"
    return "ok" if ok else "error: command rejected"


def demo():
    """固定演示：不依赖网络与交互，展示幂等性与各类边界检查。"""
    state = new_game()
    script = [
        "exchange P1 100",
        "exchange P1 100",
        "odds 100 2",
        "bet P1 200",
        "bet P1 100",
        "bet P1 1",
        "cheat",
        "cheat",
        "cancel P1",
        "cancel P1",
        "bet P1 50",
        "settle P1",
        "settle P1",
        "cheat",
        "payout P1 200",
        "payout P1 50",
        "bogus command",
        "",
    ]
    print("== 固定演示 ==")
    for line in script:
        print("> %s" % line)
        print(run_command(state, line))
    snapshot = save_state(state)
    loaded = load_state(snapshot)
    print("> save/load round_id")
    print("ok round=%s preserved=%s" % (loaded["round_id"], loaded["round_id"] == state["round_id"]))
    fault = new_game()
    run_command(fault, "exchange P2 10")
    run_command(fault, "bet P2 5")
    fault["house_fault"] = True
    print("> settle under house fault")
    print(run_command(fault, "settle P2"), "bet_kept=%s" % ("P2" in fault["bets"]))


def main():
    print("赌场 - 命令: exchange/odds/bet/cancel/settle/cheat/payout/quit")
    state = new_game()
    while True:
        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        if raw.strip() == "quit":
            break
        print(run_command(state, raw))


if __name__ == "__main__":
    main()
