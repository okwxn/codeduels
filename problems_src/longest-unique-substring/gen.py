def gen(rng, size):
    alpha = "abcdefghijklmnopqrstuvwxyz"[: rng.choice([1, 2, 3, 5, 10, 26])]
    return ["".join(rng.choice(alpha) for _ in range(size))]
