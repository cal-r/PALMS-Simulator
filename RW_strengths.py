from __future__ import annotations
from collections import deque
from functools import reduce
from itertools import combinations

class Individual:
    assoc : float
    alpha : float
    alpha_mack : float
    alpha_hall : float

    window : deque[float]
    delta_ma_hall : float

    def __init__(self, assoc = 0., alpha = .5, alpha_mack = None, alpha_hall = None, delta_ma_hall = .2, window = None):
        self.assoc = min(1., assoc)

        self.alpha = alpha
        self.alpha_mack = alpha_mack or alpha
        self.alpha_hall = alpha_hall or alpha

        if window is None:
            window = deque([])

        self.window = window.copy()
        self.delta_ma_hall = delta_ma_hall

    def join(self, other : Individual, op) -> Individual:
        ret = {}
        for prop in self.__dict__.keys():
            this = getattr(self, prop)
            that = getattr(other, prop)

            if type(this) is float or type(this) is int:
                ret[prop] = op(this, that)
            elif type(this) is deque:
                assert len(this) == len(that)
                ret[prop] = deque([op(a, b) for a, b in zip(this, that)])
            else:
                raise ValueError(f'Unknown type {type(this)} for {prop}, which is equal to {this} and {that}')

        return Individual(**ret)

    def __add__(self, other : Individual) -> Individual:
        return self.join(other, lambda a, b: a + b)

    def __truediv__(self, quot : int) -> Individual:
        ret = {}
        for prop in self.__dict__.keys():
            this = getattr(self, prop)

            if type(this) is float or type(this) is int:
                ret[prop] = this / quot
            elif type(this) is deque:
                ret[prop] = deque([a / quot for a in this]) # type: ignore
            else:
                raise ValueError(f'Unknown type {type(this)} for {prop}, which is equal to {this}')

        return Individual(**ret)

    def copy(self) -> Individual:
        return Individual(**self.__dict__)

class History:
    hist : list[Individual]

    def __init__(self):
        self.hist = []

    def add(self, ind : Individual):
        self.hist.append(ind.copy())

    def __getattr__(self, key):
        return [getattr(p, key) for p in self.hist]

class Strengths:
    cs : set[str]
    s : dict[str, Individual]

    def __init__(self, cs : None | set[str] = None, s : None | dict[str, Individual] = None):
        if cs is None and s is not None:
            cs = set(s.keys())

        if s is None and cs is not None:
            s = {k: Individual() for k in cs}

        # Weird order of ifs to make mypy happy.
        if cs is None or s is None:
            cs = set()
            s = {}

        self.cs = set(cs)
        self.s = dict(s)

    # fromHistories "transposes" a several histories of single CSs into a single list of many CSs.
    @staticmethod
    def fromHistories(histories : dict[str, History]) -> list[Strengths]:
        longest = max(len(x.hist) for x in histories.values())
        return [
            Strengths(
                s = {
                    cs: h.hist[i]
                    for cs, h in histories.items()
                    if len(h.hist) > i
                }
            )
            for i in range(longest)
        ]

    # combined_cs returns the whole list of CSs, including compound ones.
    def combined_cs(self) -> set[str]:
        h = set()

        simples = {k: v for k, v in self.s.items() if len(k) == 1}
        compounds = {k: v for k, v in self.s.items() if len(k) > 1}
        for size in range(1, len(self.s) + 1):
            for comb in combinations(simples.items(), size):
                names = [x[0] for x in comb]
                assocs = [x[1] for x in comb]
                h.add(''.join(sorted(names)))

        for k, v in compounds.items():
            h.add(k)
            h.add(f'c({k})')

        return h

    # Get the individual values of either a single key (len(key) == 1), or
    # the combined values of a combination of keys (sum of values).
    def __getitem__(self, key : str) -> Individual:
        assert len(set(key)) == len(key)
        return reduce(lambda a, b: a + b, [self.s[k] for k in key])

    def __add__(self, other : Strengths) -> Strengths:
        cs = self.cs | other.cs
        return Strengths(cs, {k: self[k] + other[k] for k in cs})

    def __truediv__(self, quot : int) -> Strengths:
        return Strengths(self.cs, {k: self.s[k] / quot for k in self.cs})

    def copy(self) -> Strengths:
        return Strengths(self.cs.copy(), {k: v.copy() for k, v in self.s.items()})

    # Returns sum of associated values
    def Sigma(self):
        return sum(x.assoc for x in self.s.values())

    @staticmethod
    def avg(val : list[Strengths]) -> Strengths:
        # We average doing `avg(X) = sum(X / n)` rather than `avg(X) = sum(X) / n`
        # since assoc values could be truncated on summation.
        val_quot = [x / len(val) for x in val]

        # We use reduce rather than sum since we don't have a zero value.
        # Python reduce is the equivalent of Haskell foldl1'.
        return reduce(lambda a, b: a + b, val_quot)
