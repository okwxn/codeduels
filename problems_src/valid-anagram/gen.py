def gen(rng, size):
    s = [rng.choice("abcde") for _ in range(size)]
    t = s[:]
    rng.shuffle(t)
    if t and rng.random() < 0.4:
        t[rng.randrange(len(t))] = rng.choice("abcdez")
    if rng.random() < 0.15:
        t.append("a")
    return ["".join(s), "".join(t)]
