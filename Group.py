from __future__ import annotations

from math import prod

from Environment import Environment, StimulusHistory, Stimulus
from AdaptiveType import AdaptiveType, RunParameters

class Group:
    name: str

    s: Environment

    adaptive_type: AdaptiveType

    @staticmethod
    def set_vals(cs: set[str], vals: dict[str, float], default: None | float) -> dict[str, float]:
        if default is None:
            return vals

        for k in cs:
            if k not in vals:
                vals[k] = prod(vals.get(x, default) for x in k.strip('()'))

        return vals

    def __init__(
        self,
        name: str,

        alphas: dict[str, float],
        default_alpha: float,
        alpha_macks: dict[str, float],
        default_alpha_mack: None | float,
        alpha_halls: dict[str, float],
        default_alpha_hall: None | float,
        saliences: dict[str, float],
        default_salience: float,
        habituations: dict[str, float],
        default_habituation: float,

        rho: float,
        nu: float,
        kay: float,
        betan: float,
        betap: float,
        lamda: float,
        gamma: float,
        thetaE: float,
        thetaI: float,
        cs: set[str] = set(),
        adaptive_type: None | str = None,
        xi_hall: None | float = None,
    ):
        cs = cs | alphas.keys() | saliences.keys() | habituations.keys() | alpha_macks.keys() | alpha_halls.keys()

        alphas = self.set_vals(cs, alphas, default_alpha)
        saliences = self.set_vals(cs, saliences, default_salience)
        alpha_macks = self.set_vals(cs, alpha_macks, default_alpha_mack)
        alpha_halls = self.set_vals(cs, alpha_halls, default_alpha_hall)
        habituations = self.set_vals(cs, habituations, default_habituation)

        self.name = name


        self.s = Environment(
            s = {
                k: Stimulus(
                    name = k,
                    alpha = alphas[k],
                    salience = saliences[k],
                    habituation = habituations[k],
                    alpha_mack = alpha_macks[k],
                    alpha_hall = alpha_halls[k],
                    rho = rho,
                    nu = nu,
                )
                for k in cs
            }
        )

        self.adaptive_type = AdaptiveType.get(
            adaptive_type,
            betan = betan,
            betap = betap,
            lamda = lamda,
            xi_hall = xi_hall,
            gamma = gamma,
            thetaE = thetaE,
            thetaI = thetaI,
            kay = kay,
        )

    # runPhase runs a single trial of a phase, in order, and returns a list of the Strength values
    # of its CS at every step.
    # It also modifies `self.s` to account for all the strengths modified in this phase.
    def runPhase(self, parts: list[tuple[str, str]], phase_beta: None | float, phase_lamda: None | float) -> list[Environment]:
        hist = StimulusHistory.emptydict()

        for part, plus in parts:
            if plus == '++':
                beta, lamda, sign = 2 * (phase_beta or self.adaptive_type.betap), phase_lamda or self.adaptive_type.lamda, 1
            elif plus == '+':
                beta, lamda, sign = phase_beta or self.adaptive_type.betap, phase_lamda or self.adaptive_type.lamda, 1
            else:
                beta, lamda, sign = self.adaptive_type.betan, 0., -1

            compounds = Environment.list_cs(part)

            rp = RunParameters(
                beta = beta,
                lamda = lamda,
                sign = sign,
                sigma = sum(self.s[x].assoc for x in compounds),
                sigmaE = sum(self.s[x].Ve for x in compounds),
                sigmaI = sum(self.s[x].Vi for x in compounds),
                count = len(compounds),
                maxAssocRest = -1,
            )

            argmaxAssoc = max(compounds, key = lambda x: self.s[x].assoc)
            maxAssoc = max(self.s[x].assoc for x in compounds)
            secondMaxAssoc = max([self.s[x].assoc for x in compounds if x != argmaxAssoc], default = 0)

            # This is a predictive model. Do not include the last stimulus in the plot.
            hist[part].add(self.s[part])
            hist[part + plus].add(self.s[part])

            for cs in compounds:
                if len(compounds) > 1:
                    hist[cs].add(self.s[cs])

                # We need to calculate max_{i != cs} V_i.
                # This is always either the maximum V_i, or the second maximum when i = cs.
                rp.maxAssocRest = maxAssoc if cs != argmaxAssoc else secondMaxAssoc
                self.adaptive_type.run_step(self.s[cs], rp)

        return Environment.fromHistories(hist)
