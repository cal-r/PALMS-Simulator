import math
from itertools import combinations
from Environment import Environment, StimulusHistory, Stimulus

class Group:
    name: str

    cs: list[str]
    s: Environment

    prev_lamda: float

    adaptive_type: None | str

    window_size: None | int
    xi_hall: None | float

    gamma: float
    thetaE: float
    thetaI: float

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
        cs = cs | alphas.keys() | saliences.keys()
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

        self.xi_hall = xi_hall

        self.betan = betan
        self.betap = betap
        self.lamda = lamda
        self.gamma = gamma
        self.thetaE = thetaE
        self.thetaI = thetaI

        self.adaptive_type = adaptive_type
        self.window_size = window_size

        self.prev_lamda = lamda

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
                beta, lamda, sign = self.betap, phase_lamda or self.lamda, 1
            else:
                beta, lamda, sign = self.betan, 0., -1

            compounds = set(part)

            sigma = sum(self.s[x].assoc for x in compounds)
            sigmaE = sum(self.s[x].Ve for x in compounds)
            sigmaI = sum(self.s[x].Vi for x in compounds)

            for cs in compounds:
                if cs not in hist:
                    hist[cs] = StimulusHistory()
                    hist[cs].add(self.s[cs])

                self.step(cs, beta, lamda, sign, sigma, sigmaE, sigmaI)

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

    def step(self, cs: str, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        delta_v_factor = beta * (self.prev_lamda - sigma)

        self.adaptive_type_but_the_class(self.s[cs], beta, lamda, sign, sigma, sigmaE, sigmaI)

        match self.adaptive_type:
            case 'rescorla_wagner':
                self.s[cs].assoc += self.s[cs].alpha * delta_v_factor

            case 'rescorla_wagner_linear':
                self.s[cs].alpha *= 1 + sign * 0.05
                self.s[cs].assoc += self.s[cs].alpha * delta_v_factor

            case 'pearce_hall':
                self.s[cs].alpha = abs(lamda - sigma)
                self.s[cs].assoc += self.s[cs].salience * self.s[cs].alpha * abs(lamda)

            case 'pearce_kaye_hall':
                rho = lamda - (sigmaE - sigmaI)

                if rho >= 0:
                    self.s[cs].Ve += self.betap * self.s[cs].alpha * lamda
                else:
                    self.s[cs].Vi += self.betan * self.s[cs].alpha * abs(rho)

                self.s[cs].alpha = self.gamma * abs(rho) + (1 - self.gamma) * self.s[cs].alpha
                self.s[cs].assoc = self.s[cs].Ve - self.s[cs].Vi

            case 'le_pelley':
                rho = lamda - (sigmaE - sigmaI)

                VXe = sigmaE - self.s[cs].Ve
                VXi = sigmaI - self.s[cs].Vi

                DVe = 0.
                DVi = 0.
                if rho >= 0:
                    DVe = self.s[cs].alpha * self.betap * (1 - self.s[cs].Ve + self.s[cs].Vi) * abs(rho)

                    if rho > 0:
                        self.s[cs].alpha += -self.thetaE * (abs(lamda - self.s[cs].Ve + self.s[cs].Vi) - abs(lamda - VXe + VXi))
                else:
                    DVi = self.s[cs].alpha * self.betan * (1 - self.s[cs].Vi + self.s[cs].Ve) * abs(rho)
                    self.s[cs].alpha += -self.thetaI * (abs(abs(rho) - self.s[cs].Vi + self.s[cs].Ve) - abs(abs(rho) - VXi + VXe))

                self.s[cs].alpha = min(max(self.s[cs].alpha, 0.05), 1)
                self.s[cs].Ve += DVe
                self.s[cs].Vi += DVi

                self.s[cs].assoc = self.s[cs].Ve - self.s[cs].Vi

            case '_rescorla_wagner_exponential':
                if sign == 1:
                    self.s[cs].alpha *= (self.s[cs].alpha ** 0.05) ** sign
                self.s[cs].assoc += self.s[cs].alpha * delta_v_factor

            case '_mack':
                self.s[cs].alpha_mack = self.get_alpha_mack(cs, sigma)
                self.s[cs].alpha = self.s[cs].alpha_mack
                self.s[cs].assoc = self.s[cs].assoc * delta_v_factor + delta_v_factor/2*beta

            case '_hall':
                self.s[cs].alpha_hall = self.get_alpha_hall(cs, sigma, self.prev_lamda)
                self.s[cs].alpha = self.s[cs].alpha_hall
                delta_v_factor = 0.5 * abs(self.prev_lamda)
                self.s[cs].assoc += self.s[cs].alpha * beta * (lamda - sigma)

            case '_macknhall':
                self.s[cs].alpha_mack = self.get_alpha_mack(cs, sigma)
                self.s[cs].alpha_hall = self.get_alpha_hall(cs, sigma, self.prev_lamda)
                self.s[cs].alpha = (1 - abs(self.prev_lamda - sigma)) * self.s[cs].alpha_mack + self.s[cs].alpha_hall
                self.s[cs].assoc += self.s[cs].alpha * delta_v_factor

            case '_newDualV':
                rho = lamda - (sigmaE - sigmaI)

                delta_ma_hall = self.s[cs].delta_ma_hall or 0
                self.gamma = 1 - math.exp(-delta_ma_hall**2)

                if rho >= 0:
                    self.s[cs].Ve += self.betap * self.s[cs].alpha * lamda
                else:
                    self.s[cs].Vi += self.betan * self.s[cs].alpha * abs(rho)

                self.s[cs].alpha = self.gamma * abs(rho) + (1 - self.gamma) * self.s[cs].alpha
                self.s[cs].assoc = self.s[cs].Ve - self.s[cs].Vi

            case '_dualmack':
                rho = lamda - (sigmaE - sigmaI)

                VXe = sigmaE - self.s[cs].Ve
                VXi = sigmaI - self.s[cs].Vi

                if rho >= 0:
                    self.s[cs].Ve += self.s[cs].alpha * self.betap * (1 - self.s[cs].Ve + self.s[cs].Vi) * abs(rho)
                else:
                    self.s[cs].Vi += self.s[cs].alpha * self.betan * (1 - self.s[cs].Vi + self.s[cs].Ve) * abs(rho)

                self.s[cs].alpha = 1/2 * (1 + self.s[cs].assoc - (VXe - VXi))
                self.s[cs].assoc = self.s[cs].Ve - self.s[cs].Vi

            case '_hybrid':
                rho = lamda - (sigmaE - sigmaI)
                
                NVe = 0.
                NVi = 0.
                if rho >= 0:
                    DVe = self.s[cs].alpha_hall * self.betap * (1 - self.s[cs].Ve + self.s[cs].Vi) * abs(rho)
                    NVe = self.s[cs].Ve + DVe
                    NVi = self.s[cs].Vi
                else:
                    NVe = self.s[cs].Ve
                    DvI = self.s[cs].alpha_hall * self.betan * (1 - self.s[cs].Vi + self.s[cs].Ve) * abs(rho)
                    NVi = self.s[cs].Vi + DvI

                VXe = sigmaE - self.s[cs].Ve
                VXi = sigmaI - self.s[cs].Vi
                if rho > 0:
                    self.s[cs].alpha_mack += -self.thetaE * (abs(lamda - self.s[cs].Ve + self.s[cs].Vi) - abs(lamda - VXe + VXi))
                elif rho < 0:
                    self.s[cs].alpha_mack += -self.thetaI * (abs(abs(rho) - self.s[cs].Vi + self.s[cs].Ve) - abs(abs(rho) - VXi + VXe))

                self.s[cs].alpha_mack = min(max(self.s[cs].alpha_mack, 0.05), 1)
                self.s[cs].alpha_hall = self.gamma * abs(rho) + (1 - self.gamma) * self.s[cs].alpha_hall

                self.s[cs].Ve = NVe
                self.s[cs].Vi = NVi

                self.s[cs].assoc = self.s[cs].alpha_mack * (self.s[cs].Ve - self.s[cs].Vi)

            case _:
                raise NameError(f'Unknown adaptive type {self.adaptive_type}!')
