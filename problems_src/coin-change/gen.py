def gen(rng, size):
    coins = rng.sample(range(1, 12), rng.randint(1, 4))
    return [coins, size]
