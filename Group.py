from Environment import Environment, StimulusHistory, Stimulus
from AdaptiveType import AdaptiveType

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
        default_alpha_mack: None | float,
        default_alpha_hall: None | float,
        saliences: dict[str, float],
        default_salience: float,
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
        cs = (cs or set()) | alphas.keys() | saliences.keys()
        if cs is not None:
            alphas = {k: alphas.get(k, default_alpha) for k in cs}
            saliences = {k: saliences.get(k, default_salience) for k in cs}

        self.name = name

        self.s = Environment(
            s = {
                k: Stimulus(assoc = 0, alpha = alphas[k], salience = saliences[k], alpha_mack = default_alpha_mack, alpha_hall = default_alpha_hall)
                for k in cs
            }
        )

        self.adaptive_type = AdaptiveType.get(adaptive_type, betan = betan, betap = betap, lamda = lamda, xi_hall = xi_hall, gamma = gamma, thetaE = thetaE, thetaI = thetaI)
        self.window_size = window_size

        # (∃ x) len(x) > 1 if `use_configurals`.
        # `use_configurals` was removed from the current version of the program,
        # but we keep this line as we might re-add it later.
        self.cs = [x for x in alphas.keys() if len(x) == 1]

    # runPhase runs a single trial of a phase, in order, and returns a list of the Strength values
    # of its CS at every step.
    # It also modifies `self.s` to account for all the strengths modified in this phase.
    def runPhase(self, parts: list[tuple[str, str]], phase_lamda: None | float) -> list[Environment]:
        hist = dict()

        for part, plus in parts:
            if plus == '+':
                beta, lamda, sign = self.adaptive_type.betap, phase_lamda or self.adaptive_type.lamda, 1
            else:
                beta, lamda, sign = self.adaptive_type.betan, 0., -1

            compounds = set(part)

            sigma = sum(self.s[x].assoc for x in compounds)
            sigmaE = sum(self.s[x].Ve for x in compounds)
            sigmaI = sum(self.s[x].Vi for x in compounds)

            for cs in compounds:
                if cs not in hist:
                    hist[cs] = StimulusHistory()
                    hist[cs].add(self.s[cs])

                self.adaptive_type.run_step(self.s[cs], beta, lamda, sign, sigma, sigmaE, sigmaI)

                if self.window_size is not None:
                    if len(self.s[cs].window) >= self.window_size:
                        self.s[cs].window.popleft()

                    self.s[cs].window.append(self.s[cs].assoc)
                    window_avg = sum(self.s[cs].window) / len(self.s[cs].window)

                    # delta_ma_hall is modified using the previous associated value.
                    self.s[cs].delta_ma_hall = window_avg - hist[cs].assoc[-1]

                hist[cs].add(self.s[cs])
            self.prev_lamda = lamda

        return Environment.fromHistories(hist)
