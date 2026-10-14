def gen(rng, size):
    n = max(2, size)
    twos = 0
    nums = []
    for _ in range(n):
        if rng.random() < 1.5 / n:
            x = 0
        else:
            x = rng.choice([-1, 1, 1, 2])
        if x == 2:
            twos += 1
            if twos > 30:
                x = 1
        nums.append(x)
    return [nums]
