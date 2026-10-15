def gen(rng, size):
    half = "".join(rng.choice("abAB12") for _ in range(size // 2))
    core = half + rng.choice(["", "a", "Z", "7"]) + half[::-1]
    if core and rng.random() < 0.5:  # sometimes break the palindrome
        i = rng.randrange(len(core))
        core = core[:i] + rng.choice("abAB12xy") + core[i + 1 :]
    out = []
    for c in core:
        out.append(c.swapcase() if rng.random() < 0.3 else c)
        if rng.random() < 0.2:
            out.append(rng.choice(" ,.:;!?-'"))
    return ["".join(out)]
