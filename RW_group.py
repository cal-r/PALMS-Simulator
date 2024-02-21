import math
from collections import deque, defaultdict
from typing import List
from itertools import combinations

class Group:
    def __init__(self, name, alphas, betan, betap, lamdan, lamdap, cs = None, use_configurals = False, adaptive_type = None, window_size = None, xi_hall = None):
        # If some alphas don't appear, set their alpha to 0.2.
        if cs is not None:
            alphas = {k: alphas.get(k, 0.2) for k in cs | alphas.keys()}

        self.name = name
        self.alphas_copy = alphas.copy()
        self.alphas = self.alphas_copy

        self.alpha_mack = {k: 0 for k in cs}
        self.alpha_hall = {k: 0 for k in cs}

        # self.delta_ma_hall is the difference of the moving averages used for Hall.
        # self.delta_ma_hall^n = V^n_{MA} - V^{n - 1}_{MA}
        self.delta_ma_hall = {k: None for k in cs}
        self.xi_hall = xi_hall

        self.betan = betan
        self.betap = betap
        self.lamdan = lamdan
        self.lamdap = lamdap
        self.use_configurals = use_configurals
        self.adaptive_type = adaptive_type
        self.window_size = window_size

        self.window = defaultdict(lambda: deque())

        # For simplicity, if we use_configurals and some compound stimuli don't
        # have a corresponding \alpha, then we calculate it as the product
        # of their simple stimuli.
        self.cs = [x for x in alphas.keys() if len(x) == 1]
        if use_configurals:
            simples = {k: v for k, v in alphas.items() if len(k) == 1}
            compounds = {
                ''.join(p[0] for p in x): math.prod(p[1] for p in x)
                for x in sum(
                    [
                        list(combinations(simples.items(), t))
                        for t in range(1, len(simples) + 1)
                    ],
                    []
                )
            }
            self.alphas = compounds | alphas
            self.cs = self.alphas.keys()

        # The initial associative strength for all stimuli is 0.
        self.assoc = {c: 0. for c in self.cs}

    # This is a helper method that combines all stimuli into compound stimuli.
    # If we are using configural cues, then these are added to the value and
    # returned separately.
    @staticmethod
    def combine(V):
        h = dict()

        simples = {k: v for k, v in V.items() if len(k) == 1}
        compounds = {k: v for k, v in V.items() if len(k) > 1}
        for size in range(1, len(V) + 1):
            for comb in combinations(simples.items(), size):
                names = [x[0] for x in comb]
                assocs = [x[1]for x in comb]
                h[''.join(names)] = [min(1, sum(x)) for x in zip(*assocs)]

        for k, v in compounds.items():
            h[k] = [x + y for x, y in zip(h[k], v)]
            h[f'c({k})'] = v

        return h

    def get_alpha_mack(self, cs):
        big_mack_error = sum(self.assoc.values()) / len(self.assoc) - self.assoc[cs]
        return self.alpha_mack[cs] - big_mack_error

    def get_alpha_hall(self, cs):
        if self.window_size is None:
            return None

        if self.delta_ma_hall[cs] is None:
            return 0

        error = self.xi_hall * self.alpha_hall[cs] * math.exp(-self.delta_ma_hall[cs] ** 2 / 2)
        return self.alpha_hall[cs] + error

    def compounds(self, part : str):
        compounds = set(part)
        if self.use_configurals:
            compounds.add(part)

        return compounds

    def runPhase(self, parts : List[str]):
        V = dict()
        A = dict()

        A_mack = dict()
        A_hall = dict()

        for part, plus in parts:
            beta = self.betap
            lamda = self.lamdap
            sign = 1
            if not plus == '+':
                beta = self.betan
                lamda = self.lamdan
                sign = -1

            compounds = self.compounds(part)
            sigma = sum(self.assoc[x] for x in compounds)
            for cs in compounds:
                if cs not in V:
                    V[cs] = [self.assoc[cs]]
                    A[cs] = [self.alphas[cs]]

                self.alpha_mack[cs] = self.get_alpha_mack(cs)
                self.alpha_hall[cs] = self.get_alpha_hall(cs)
                
                match self.adaptive_type:
                    case 'linear':
                        self.alphas[cs] *= 1 + sign * 0.05
                    case 'exponential':
                        if sign == 1:
                            self.alphas[cs] *= (self.alphas[cs] ** 0.05) ** sign

                self.assoc[cs] += self.alphas[cs] * beta * (lamda - sigma)

                if self.window_size is not None:
                    if len(self.window[cs]) >= self.window_size:
                        self.window[cs].popleft()

                    self.window[cs].append(self.assoc[cs])

                    window_avg = sum(self.window[cs]) / len(self.window[cs])

                    self.delta_ma_hall[cs] = window_avg - V[cs][-1]
                    V[cs].append(window_avg)
                else:
                    V[cs].append(self.assoc[cs])

                A[cs].append(self.alphas[cs])

        return self.combine(V), A
