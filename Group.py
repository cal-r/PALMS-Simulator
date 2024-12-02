from __future__ import annotations

from Environment import Environment, StimulusHistory, Stimulus
from AdaptiveType import AdaptiveType, RunParameters

class Group:
    name: str

    cs: list[str]
    s: Environment

    adaptive_type: AdaptiveType
    window_size: None | int

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
        cs: None | set[str] = None,
        adaptive_type: None | str = None,
        window_size: None | int = None,
        xi_hall: None | float = None,
    ):
        cs = (cs or set()) | alphas.keys() | saliences.keys() | habituations.keys() | alpha_macks.keys() | alpha_halls.keys()
        if cs is not None:
            alphas = {k: alphas.get(k, default_alpha) for k in cs}
            saliences = {k: saliences.get(k, default_salience) for k in cs}
            habituations = {k: habituations.get(k, default_salience) for k in cs}
            alpha_macks = {k: alpha_macks.get(k, default_alpha_mack) for k in cs}
            alpha_halls = {k: alpha_halls.get(k, default_alpha_hall) for k in cs}

        self.name = name

        self.s = Environment(
            s = {
                k: Stimulus(
                    assoc = 0,
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

        self.adaptive_type = AdaptiveType.get(adaptive_type, betan = betan, betap = betap, lamda = lamda, xi_hall = xi_hall, gamma = gamma, thetaE = thetaE, thetaI = thetaI, kay = kay)
        self.window_size = window_size

        # (∃ x) len(x) > 1 if `use_configurals`.
        # `use_configurals` was removed from the current version of the program,
        # but we keep this line as we might re-add it later.
        self.cs = [x for x in alphas.keys() if len(x) == 1]

    # runPhase runs a single trial of a phase, in order, and returns a list of the Strength values
    # of its CS at every step.
    # It also modifies `self.s` to account for all the strengths modified in this phase.
    def runPhase(self, parts: list[tuple[str, str]], phase_lamda: None | float) -> list[Environment]:
        hist = StimulusHistory.emptydict()

        for part, plus in parts:
            if plus == '+':
                beta, lamda, sign = self.adaptive_type.betap, phase_lamda or self.adaptive_type.lamda, 1
            else:
                beta, lamda, sign = self.adaptive_type.betan, 0., -1

            compounds = set(part)

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
            secondMaxAssoc = max([self.s[x].assoc for x in compounds - {argmaxAssoc}], default = 0)

            for cs in compounds:
                if cs not in hist:
                    hist[cs].add(self.s[cs])

                # We need to calculate max_{i != cs} V_i.
                # This is always either the maximum V_i, or the second maximum when i = cs.
                rp.maxAssocRest = maxAssoc if cs != argmaxAssoc else secondMaxAssoc
                self.adaptive_type.run_step(self.s[cs], rp)

                if self.window_size is not None:
                    if len(self.s[cs].window) >= self.window_size:
                        self.s[cs].window.popleft()

                    self.s[cs].window.append(self.s[cs].assoc)
                    window_avg = sum(self.s[cs].window) / len(self.s[cs].window)

                    # delta_ma_hall is modified using the previous associated value.
                    self.s[cs].delta_ma_hall = window_avg - hist[cs].assoc[-1]

                hist[cs].add(self.s[cs])

        return Environment.fromHistories(hist)
