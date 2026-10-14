def gen(rng, size):
    if rng.random() < 0.5:
        return [rng.sample(range(-2 * size - 1, 2 * size + 1), size)]
    return [[rng.randint(-size, size) for _ in range(size)]]
