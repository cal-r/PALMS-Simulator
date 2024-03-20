import math
from collections import deque, defaultdict
from typing import List
from itertools import combinations
import numpy as np

class Group:
    def __init__(self, name, alphas, betan, betap, lamda, cs = None, use_configurals = False, adaptive_type = None, window_size = None, xi_hall = None):
        # If some alphas don't appear, set their alpha to 0.

# Initially, alpha_mack and alpha_hall are identical.
        if cs is not None:
            self.alpha_mack = {k: 0.5 for k in cs}
            self.alpha_hall = {k: 0.5 for k in cs}
        else:
            self.alpha_mack = {k: 0.5 for k in alphas.keys()}
            self.alpha_hall = {k: 0.5 for k in alphas.keys()}

        if cs is not None:
            init_value = max(max(list(self.alpha_mack.values()), list(self.alpha_hall.values())))
            alphas = {k: alphas.get(k, init_value) for k in cs | alphas.keys()}

        self.name = name
        self.alphas_copy = alphas.copy()
        self.alphas = self.alphas_copy

        # self.delta_ma_hall is the difference of the moving averages used for Hall.
        # self.delta_ma_hall^n = V^n_{MA} - V^{n - 1}_{MA}
        self.delta_ma_hall = {k: None for k in cs}
        self.xi_hall = xi_hall

        self.betan = betan
        self.betap = betap
        self.lamda = lamda
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

    def get_alpha_mack(self, cs, sigma):
        # This overflows -- ask Esther.
        # big_mack_error = sum(self.assoc.values()) / len(self.assoc) - self.assoc[cs]
        # return self.alpha_mack[cs] - big_mack_error
        #return 0
        """if len(self.assoc) > 1:
            big_mack_error = ( sum(self.assoc[x] for x in self.assoc if x!=cs)/ (len(self.assoc)-1) ) - self.assoc[cs]
        else:
            big_mack_error = - self.assoc[cs]
        return self.alpha_mack[cs] - 0.2*big_mack_error"""
        
        #return self.alpha_mack[cs] + 0.01*self.assoc[cs]
        #print((1 + (2*self.assoc[cs] - sigma))/2)
        return ((1 + (2*self.assoc[cs] - sigma))/2)
        #return self.alpha_mack[cs]*(1 + (2*self.assoc[cs] - sum(self.assoc.values())))/2
        #return self.alpha_mack[cs] + 0.01*(2*self.assoc[cs] - sum(self.assoc.values()))

    def get_alpha_hall(self, cs, sigma, lamda):
        assert self.window_size is not None

        delta_ma_hall = self.delta_ma_hall[cs]
        if delta_ma_hall is None:
            delta_ma_hall = 0

        try:
            #error = (self.alpha_hall[cs] * (1-self.xi_hall*math.exp(- delta_ma_hall**2 / 2)))
            print("HALL")
            print(1-lamda+sigma)
            error = (((1-lamda+sigma) * self.alpha_hall[cs] * (1-self.xi_hall*math.exp(- delta_ma_hall**2 / 2)))+lamda-sigma)/2

        except:
            error = ((1-lamda+sigma)*self.alpha_hall[cs] + lamda-sigma)/2
        print(f"alpha_hall: {error}")
        return error

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
            lamda = self.lamda
            sign = 1
            if not plus == '+':
                beta = self.betan
                lamda = 0
                sign = -1

            compounds = self.compounds(part)
            sigma = sum(self.assoc[x] for x in compounds)
            for cs in compounds:
                if cs not in V:
                    V[cs] = [self.assoc[cs]]
                    A[cs] = [self.alphas[cs]]
                    A_mack[cs] = [self.alpha_mack[cs]]
                    A_hall[cs] = [self.alpha_hall[cs]]

                self.alpha_mack[cs] = self.get_alpha_mack(cs, sigma)
                self.alpha_hall[cs] = self.get_alpha_hall(cs, sigma, lamda)
                
                match self.adaptive_type:
                    case 'linear':
                        self.alphas[cs] *= 1 + sign * 0.05
                    case 'exponential':
                        if sign == 1:
                            self.alphas[cs] *= (self.alphas[cs] ** 0.05) ** sign
                    case 'macknhall':
                        self.alphas[cs] = (1-lamda+sigma) * self.alpha_mack[cs] + (lamda-sigma) * self.alpha_hall[cs]
                        """delta_v_n = self.alpha_hall[cs] * beta * (lamda - sigma)
                        v_n = self.alpha_mack[cs] * self.assoc[cs]
                        self.assoc[cs] = v_n + delta_v_n"""

                print(f"DV: {self.alphas[cs] * beta * (lamda - sigma)}, Alpha: {self.alphas[cs]}, sigma: {sigma}")
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
                A_mack[cs].append(self.alpha_mack[cs])
                A_hall[cs].append(self.alpha_hall[cs])

        return self.combine(V), A, A_mack, A_hall