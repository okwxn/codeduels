def gen(rng, size):
    side = max(1, int(size**0.5))
    density = rng.choice([0.2, 0.4, 0.6])
    return [
        [[1 if rng.random() < density else 0 for _ in range(side)] for _ in range(side)]
    ]
