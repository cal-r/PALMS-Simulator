import math
from itertools import combinations
from RW_strengths import Strengths, History, Individual

class Group:
    name : str

    cs : list[str]
    s : Strengths

    betan : float
    betap : float
    lamda : float

    prev_lamda : float

    use_configurals : bool
    adaptive_type : None | str

    window_size : None | int
    xi_hall : None | float

    def __init__(self, name : str, alphas : dict[str, float], default_alpha : float, betan : float, betap : float, lamda : float, gamma : float, thetaE : float, thetaI : float, cs : None | set[str] = None, use_configurals : bool = False, adaptive_type : None | str = None, window_size : None | int = None, xi_hall : None | float = None):
        if cs is not None:
            alphas = {k: alphas.get(k, default_alpha) for k in cs | alphas.keys()}

        self.name = name

        self.s = Strengths(
            s = {
                k: Individual(assoc = 0, alpha = alphas[k])
                for k in alphas.keys()
            }
        )

        self.xi_hall = xi_hall

        self.betan = betan
        self.betap = betap
        self.lamda = lamda
        self.gamma = gamma
        self.thetaE = thetaE
        self.thetaI = thetaI

        self.use_configurals = use_configurals
        self.adaptive_type = adaptive_type
        self.window_size = window_size

        self.prev_lamda = 0

        # For simplicity, if we use_configurals and some compound stimuli don't
        # have a corresponding \alpha, then we calculate it as the product
        # of their simple stimuli.
        self.cs = [x for x in alphas.keys() if len(x) == 1]

        # use_configurals is not working with strengths - add it later.
        '''
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
        '''

    def get_alpha_mack(self, cs : str, sigma : float) -> float:
        return 1/2 * (1 + (2 * self.s[cs].assoc - sigma))

    def get_alpha_hall(self, cs : str, sigma : float, lamda : float) -> float:
        assert self.xi_hall is not None

        delta_ma_hall = self.s[cs].delta_ma_hall or 0

        surprise = abs(lamda - sigma)
        window_term =  1 - self.xi_hall * math.exp(-delta_ma_hall**2 / 2)
        gamma = 0.99
        kayes = gamma*surprise +  (1-gamma)*self.s[cs].alpha_hall

        new_error = kayes

        # error = 1/2 * ((1 - surprise) * self.s[cs].alpha_hall * window_term + surprise)
        # error = 1/2 * ((1 - surprise) * self.s[cs].alpha_hall * window_term + surprise*(1-self.s[cs].alpha_hall))
        # error = self.s[cs].alpha_hall + window_term

        return new_error

    # compounds should probably be moved to Strengths.
    def compounds(self, part : str) -> set[str]:
        compounds = set(part)
        if self.use_configurals:
            compounds.add(part)

        return compounds

    # runPhase runs a single trial of a phase, in order, and returns a list of the Strength values
    # of its CS at every step.
    # It also modifies `self.s` to account for all the strengths modified in this phase.
    def runPhase(self, parts : list[tuple[str, str]], phase_lamda : None | float) -> list[Strengths]:
        hist = dict()

        for part, plus in parts:
            if plus == '+':
                beta, lamda, sign = self.betap, phase_lamda or self.lamda, 1
            else:
                beta, lamda, sign = self.betan, 0., -1

            compounds = self.compounds(part)

            sigma = sum(self.s[x].assoc for x in compounds)
            sigmaE = sum(self.s[x].Ve for x in compounds)
            sigmaI = sum(self.s[x].Vi for x in compounds)

            for cs in compounds:
                if cs not in hist:
                    hist[cs] = History()
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

        return Strengths.fromHistories(hist)

    def step(self, cs: str, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        delta_v_factor = beta * (self.prev_lamda - sigma)

        match self.adaptive_type:
            case 'linear':
                self.s[cs].alpha *= 1 + sign * 0.05
                self.s[cs].assoc += self.s[cs].alpha * delta_v_factor

            case 'exponential':
                if sign == 1:
                    self.s[cs].alpha *= (self.s[cs].alpha ** 0.05) ** sign
                self.s[cs].assoc += self.s[cs].alpha * delta_v_factor

            case 'mack':
                self.s[cs].alpha_mack = self.get_alpha_mack(cs, sigma)
                self.s[cs].alpha = self.s[cs].alpha_mack
                self.s[cs].assoc += self.s[cs].alpha * delta_v_factor

            case 'hall':
                self.s[cs].alpha_hall = self.get_alpha_hall(cs, sigma, self.prev_lamda)
                self.s[cs].alpha = self.s[cs].alpha_hall
                delta_v_factor = 0.5 * abs(self.prev_lamda)
                self.s[cs].assoc += self.s[cs].alpha * delta_v_factor

            case 'macknhall':
                self.s[cs].alpha_mack = self.get_alpha_mack(cs, sigma)
                self.s[cs].alpha_hall = self.get_alpha_hall(cs, sigma, self.prev_lamda)
                self.s[cs].alpha = (1 - abs(self.prev_lamda - sigma)) * self.s[cs].alpha_mack + self.s[cs].alpha_hall
                self.s[cs].assoc += self.s[cs].alpha * delta_v_factor

            case 'dualV':
                # Ask Esther whether this is lamda^{n + 1) or lamda^n.
                rho = lamda - (sigmaE - sigmaI)

                if rho >= 0:
                    self.s[cs].Ve += self.betap * self.s[cs].alpha * lamda
                else:
                    self.s[cs].Vi += self.betan * self.s[cs].alpha * abs(rho)

                self.s[cs].alpha = self.gamma * abs(rho) + (1 - self.gamma) * self.s[cs].alpha
                self.s[cs].assoc = self.s[cs].Ve - self.s[cs].Vi

            case 'lepelley':
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

            case 'dualmack':
                rho = lamda - (sigmaE - sigmaI)

                VXe = sigmaE - self.s[cs].Ve
                VXi = sigmaI - self.s[cs].Vi

                if rho >= 0:
                    self.s[cs].Ve += self.s[cs].alpha * self.betap * (1 - self.s[cs].Ve + self.s[cs].Vi) * abs(rho)
                else:
                    self.s[cs].Vi += self.s[cs].alpha * self.betan * (1 - self.s[cs].Vi + self.s[cs].Ve) * abs(rho)

                self.s[cs].alpha = 1/2 * (1 + self.s[cs].assoc - (VXe - VXi))
                self.s[cs].assoc = self.s[cs].Ve - self.s[cs].Vi

            case 'hybrid':
                rho = lamda - (sigmaE - sigmaI)

                NVe = 0.
                NVi = 0.
                if rho >= 0:
                    NVe = self.s[cs].alpha_mack * self.s[cs].Ve + self.betap * self.s[cs].alpha_hall * lamda
                    NVi = self.s[cs].Vi
                else:
                    NVe = self.s[cs].Ve
                    NVi = self.s[cs].alpha_mack * self.s[cs].Vi + self.betan * self.s[cs].alpha_hall * abs(rho)

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

                self.s[cs].assoc = self.s[cs].Ve - self.s[cs].Vi

                print(f'{cs}:\t𝛒 = {rho:.3f}; Ve = {self.s[cs].Ve:.3f}; Vi = {self.s[cs].Vi:.3f}')

            case _:
                raise NameError(f'Unknown adaptive type {self.adaptive_type}!')
