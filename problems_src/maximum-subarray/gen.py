def gen(rng, size):
    n = max(1, size)
    return [[rng.randint(-10, 10) for _ in range(n)]]
