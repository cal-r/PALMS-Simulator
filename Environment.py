from __future__ import annotations
from collections import deque, defaultdict
from functools import reduce
from itertools import combinations

from typing import Any, ClassVar

import re

class Stimulus:
    name: str

    assoc: float

    Ve: float
    Vi: float

    alpha: float
    alpha_mack: float
    alpha_hall: float

    salience: float
    habituation: float

    rho: float
    nu: float

    window: deque[float]
    delta_ma_hall: float

    alpha_mack_0: float
    alpha_hall_0: float

    def __init__(
            self,
            name: str,
            *,
            alpha, alpha_mack, alpha_hall,
            salience, habituation,
            rho, nu,
            assoc = 0.,
            Ve = 0., Vi = 0.,
            delta_ma_hall = .2,
            window: None | deque = None,
            alpha_mack_0 = None, alpha_hall_0 = None,
        ):
        self.name = name

        self.assoc = assoc

        self.Ve = Ve
        self.Vi = Vi

        self.alpha = alpha
        self.alpha_mack = alpha_mack
        self.alpha_hall = alpha_hall

        self.salience =  salience
        self.habituation = habituation

        self.rho = rho
        self.nu = nu

        self.alpha_mack_0 = alpha_mack_0 or self.alpha_mack
        self.alpha_hall_0 = alpha_hall_0 or self.alpha_hall

        if window is None:
            window = deque([])

        self.window = window.copy()
        self.delta_ma_hall = delta_ma_hall

    def join(self, other: Stimulus, op) -> Stimulus:
        ret: dict[str, Any] = dict(
            name = ''.join(sorted(set(self.splitName() + other.splitName())))
        )

        for prop in self.__dict__.keys():
            if prop == 'name':
                continue

            this = getattr(self, prop)
            that = getattr(other, prop)

            if type(this) is float or type(this) is int:
                ret[prop] = op(this, that)
            elif type(this) is deque:
                size = max(len(this), len(that))
                this = deque([0] * (size - len(this))) + this
                that = deque([0] * (size - len(that))) + that
                ret[prop] = deque([op(a, b) for a, b in zip(this, that)])
            else:
                raise ValueError(f'Unknown type {type(this)} for {prop}, which is equal to {this} and {that}')

        return Stimulus(**ret)

    def __add__(self, other: Stimulus) -> Stimulus:
        return self.join(other, lambda a, b: a + b)

    def __truediv__(self, quot: int) -> Stimulus:
        ret: dict[str, Any] = dict(name = self.name)
        for prop in self.__dict__.keys():
            if prop == 'name':
                continue

            this = getattr(self, prop)

            if type(this) is float or type(this) is int:
                ret[prop] = this / quot
            elif type(this) is deque:
                ret[prop] = deque([a / quot for a in this]) # type: ignore
            else:
                raise ValueError(f'Unknown type {type(this)} for {prop}, which is equal to {this}')

        return Stimulus(**ret)

    def copy(self) -> Stimulus:
        return Stimulus(**self.__dict__)

    def splitName(self) -> list[str]:
        return Environment.split_cs(self.name)

class StimulusHistory:
    hist: list[Stimulus]

    def __init__(self, hist: None | list[Stimulus] = None):
        self.hist = hist or []

    def add(self, ind: Stimulus):
        self.hist.append(ind.copy())

    def __getattr__(self, key):
        return [getattr(p, key) for p in self.hist]

    def __len__(self):
        return len(self.hist)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return StimulusHistory(self.hist[key])

        return self.hist[key]

    @classmethod
    def emptydict(cls) -> dict[str, StimulusHistory]:
        return defaultdict(lambda: StimulusHistory())

class Environment:
    # Static class variable indicating whether to use configural cues.
    configural_cues: ClassVar[bool] = False

    # Dictionary with all singular CS -> stimuli.
    # Values should be begotten with `env[cs]`, where `cs` can be singular
    # or multiple CSs together.
    s: dict[str, Stimulus]

    def __init__(self, s: dict[str, Stimulus]):
        self.s = s

    # fromHistories "transposes" a several histories of single CSs into a single list of many CSs.
    @staticmethod
    def fromHistories(histories: dict[str, StimulusHistory]) -> list[Environment]:
        longest = max((len(x.hist) for x in histories.values()), default = 0)
        return [
            Environment(
                s = {
                    cs: h.hist[i]
                    for cs, h in histories.items()
                    if len(h.hist) > i
                },
            )
            for i in range(longest)
        ]

    # Splits a compound CS into its constituent parts.
    # split_cs("AA'A''A'''BC''") = ["A", "A'", "A''", "A'''", "B", "C''"]
    @staticmethod
    def split_cs(cs) -> list[str]:
        values = sorted(re.findall(r"[a-zA-ZñÑ]'*|\((?:[a-zA-ZñÑ]'*)+\)", cs))
        if len(''.join(set(values))) != len(cs):
            raise ValueError(f'"{cs}" cannot be split into unique separate CS.')

        return values

    # Same as split_cs, but adds configural cues if necessary.
    @classmethod
    def list_cs(cls, cs) -> list[str]:
        values = cls.split_cs(cs)
        if cls.configural_cues and len(values) > 1:
            values += [f'({cs})']

        return values

    # Get the individual values of either a single key (len(key) == 1), or
    # the combined values of a combination of keys (sum of values).
    def __getitem__(self, key: str) -> Stimulus:
        return reduce(lambda a, b: a + b, [self.s[k] for k in self.list_cs(key)])

    def filter_keys(self, keys: list[str]) -> list[str]:
        return [k for k in keys if all(t in self.s for t in self.list_cs(k))]

    def __add__(self, other: Environment) -> Environment:
        cs = self.s.keys() | other.s.keys()
        return Environment({k: self[k] + other[k] for k in cs})

    def __truediv__(self, quot: int) -> Environment:
        return Environment({k: self.s[k] / quot for k in self.s.keys()})

    def copy(self) -> Environment:
        return Environment({k: v.copy() for k, v in self.s.items()})

    @staticmethod
    def avg(val: list[Environment]) -> Environment:
        # We average doing `avg(X) = sum(X / n)` rather than `avg(X) = sum(X) / n`
        # since assoc values could be truncated on summation.
        val_quot = [x / len(val) for x in val]

        # We use reduce rather than sum since we don't have a zero value.
        # Python reduce is the equivalent of Haskell foldl1'.
        return reduce(lambda a, b: a + b, val_quot)

    def assocs(self) -> dict[str, float]:
        return {k: v.assoc for k, v in self.s.items()}
