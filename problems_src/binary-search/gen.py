def gen(rng, size):
    nums = sorted(rng.sample(range(-3 * size - 5, 3 * size + 5), size))
    if nums and rng.random() < 0.6:
        t = rng.choice(nums)
    else:
        t = rng.randint(-3 * size - 8, 3 * size + 8)
    return [nums, t]
