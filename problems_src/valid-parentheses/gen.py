def gen(rng, size):
    pairs = ["()", "[]", "{}"]
    out, stack = [], []
    for _ in range(size):
        if stack and rng.random() < 0.5:
            out.append(stack.pop())
        else:
            o = rng.choice(pairs)
            out.append(o[0])
            stack.append(o[1])
    while stack:
        out.append(stack.pop())
    if out and rng.random() < 0.4:
        out[rng.randrange(len(out))] = rng.choice("()[]{}")
    return ["".join(out)]
