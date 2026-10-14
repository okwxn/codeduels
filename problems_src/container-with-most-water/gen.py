def gen(rng, size):
    n = max(2, size)
    return [[rng.randint(0, 60) for _ in range(n)]]
