def check(args, got, expected):
    nums, target = args
    return (isinstance(got, list) and len(got) == 2 and got[0] != got[1]
            and all(isinstance(i, int) and 0 <= i < len(nums) for i in got)
            and nums[got[0]] + nums[got[1]] == target)