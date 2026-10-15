def gen(rng, size):
    n = max(2, size)
    nums = rng.sample(range(-10 * n, 10 * n), n)
    i, j = rng.sample(range(n), 2)
    return [nums, nums[i] + nums[j]]
