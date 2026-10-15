def solve(grid):
    cells = (
        [
            (r, c)
            for r in range(len(grid))
            for c in range(len(grid[0]))
            if grid[r][c] == 1
        ]
        if grid
        else []
    )
    parent = {p: p for p in cells}

    def find(p):
        while parent[p] != p:
            p = parent[p]
        return p

    for r, c in cells:
        for q in ((r + 1, c), (r, c + 1)):
            if q in parent:
                a, b = find((r, c)), find(q)
                if a != b:
                    parent[a] = b
    return len({find(p) for p in cells})
