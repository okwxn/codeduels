def solve(coins, amount):
    seen = {0}
    frontier = [0]
    steps = 0
    while frontier:
        if amount in seen:
            return steps
        steps += 1
        nxt = []
        for v in frontier:
            for c in coins:
                w = v + c
                if w <= amount and w not in seen:
                    seen.add(w)
                    nxt.append(w)
        frontier = nxt
    return -1
