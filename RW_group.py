import math
from itertools import combinations

class Group:
    def __init__(self, alphas, betan, betap, lamdan, lamdap, cs = None, use_configurals = False, use_adaptive = False):
        # If some alphas don't appear, set their alpha to 0.2.
        if cs is not None:
            alphas = {k: alphas.get(k, 0.2) for k in cs | alphas.keys()}

        self.alphas_copy = alphas.copy()
        self.alphas = self.alphas_copy
        self.betan = betan
        self.betap = betap
        self.lamdan = lamdan
        self.lamdap = lamdap
        self.use_configurals = use_configurals
        self.use_adaptive = use_adaptive

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
                assocs = [x[1] for x in comb]
                h[''.join(names)] = [min(1, sum(x)) for x in zip(*assocs)]

        for k, v in compounds.items():
            h[k] = [x + y for x, y in zip(h[k], v)]
            h[f'c({k})'] = v

        return h

    # Run a single phase of the experiment consisting of `steps` steps of
    # certain CS `conds`, either with the associated US `plus` or not `not plus`.
    # Its return value is the `V` dict of arrays corresponding to each element
    # in `conds` if `ret_V`, and `self` otherwise.
    def runPhase(self, steps, conds, plus = True, ret_V = False):
        beta = self.betan
        lamda = self.lamdan
        if plus:
            beta = self.betap
            lamda = self.lamdap

        # If `not use_configurals`, we only care about the individual compounds.
        # Otherwise, we also care about the configural cue of the final compound.
        compounds = list(conds)
        if self.use_configurals:
            compounds.append(conds)

        try:
            V = {x: [self.assoc[x]] for x in compounds}
        except KeyError as exc:
            exc.add_note(f'Not all stimuli in {compounds} have an associative value. Did you forget to add an --alpha?')
            raise exc

        for step in range(steps):
            # `sigma` is the global error at this stage.            
            sigma = sum(self.assoc[x] for x in compounds)
            for cs in compounds:
                if self.use_adaptive:
                    if not plus and self.alphas[cs] > 0:
                        self.alphas[cs] -= self.alphas[cs]*0.05
                    else:
                        self.alphas[cs] += self.alphas[cs]*0.05

                self.assoc[cs] += self.alphas[cs] * beta * (lamda - sigma)
                V[cs].append(self.assoc[cs])

        if ret_V:
            return self.combine(V)

        return self
