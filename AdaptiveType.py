from __future__ import annotations

import math
from typing import Type

from Environment import Stimulus

class AdaptiveType:
    betan: float
    betap: float
    lamda: float
    xi_hall: None | float
    gamma: float
    thetaE: float
    thetaI: float

    prev_lamda: float

    def __init__(self, betan: float, betap: float, lamda: float, xi_hall: None | float, gamma: float, thetaE: float, thetaI: float):
        self.betan = betan
        self.betap = betap
        self.lamda = lamda
        self.xi_hall = xi_hall
        self.gamma = gamma
        self.thetaE = thetaE
        self.thetaI = thetaI
        self.prev_lamda = lamda

    @classmethod
    def types(cls) -> dict[str, Type[AdaptiveType]]:
        return {
            'rescorla_wagner': RescorlaWagner,
            'rescorla_wagner_linear': RescorlaWagnerLinear,
            'pearce_hall': PearceHall,
            'pearce_kaye_hall': PearceKayeHall,
            'le_pelley': LePelley,
            'rescorla_wagner_exponential': RescorlaWagnerExponential,
            'mack': Mack,
            'hall': Hall,
            'macknhall': Macknhall,
            'new_dual_v': NewDualV,
            'dualmack': Dualmack,
            'hybrid': Hybrid,
        }

    @classmethod
    def get(cls, adaptive_type_name, *args, **kwargs) -> AdaptiveType:
        return cls.types()[adaptive_type_name](*args, **kwargs)

    def get_alpha_mack(self, s: Stimulus, sigma: float) -> float:
        return 1/2 * (1 + 2*s.assoc - sigma)

    def get_alpha_hall(self, s: Stimulus, sigma: float, lamda: float) -> float:
        assert self.xi_hall is not None

        delta_ma_hall = s.delta_ma_hall or 0

        surprise = abs(lamda - sigma)
        window_term =  1 - self.xi_hall * math.exp(-delta_ma_hall**2 / 2)
        gamma = 0.99
        kayes = gamma*surprise +  (1-gamma)*s.alpha_hall

        new_error = kayes

        return new_error

    def run_step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        self.delta_v_factor = beta * (self.prev_lamda - sigma)
        self.step(s, beta, lamda, sign, sigma, sigmaE, sigmaI)
        self.prev_lamda = lamda

    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        raise NotImplementedError('Calling step in abstract function is undefined.')

class RescorlaWagner(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        s.assoc += s.alpha * self.delta_v_factor

class RescorlaWagnerLinear(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        s.alpha *= 1 + sign * 0.05
        s.alpha = min(max(s.alpha, 0.05), 1)
        s.assoc += s.alpha * self.delta_v_factor

class PearceHall(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        s.alpha = abs(lamda - sigma)
        s.assoc += s.salience * s.alpha * abs(lamda)

class PearceKayeHall(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        rho = lamda - (sigmaE - sigmaI)

        if rho >= 0:
            s.Ve += self.betap * s.alpha * lamda
        else:
            s.Vi += self.betan * s.alpha * abs(rho)

        s.alpha = self.gamma * abs(rho) + (1 - self.gamma) * s.alpha
        s.assoc = s.Ve - s.Vi

class LePelley(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        rho = lamda - (sigmaE - sigmaI)

        VXe = sigmaE - s.Ve
        VXi = sigmaI - s.Vi

        DVe = 0.
        DVi = 0.
        if rho >= 0:
            DVe = s.alpha * self.betap * (1 - s.Ve + s.Vi) * abs(rho)

            if rho > 0:
                s.alpha += -self.thetaE * (abs(lamda - s.Ve + s.Vi) - abs(lamda - VXe + VXi))
        else:
            DVi = s.alpha * self.betan * (1 - s.Vi + s.Ve) * abs(rho)
            s.alpha += -self.thetaI * (abs(abs(rho) - s.Vi + s.Ve) - abs(abs(rho) - VXi + VXe))

        s.alpha = min(max(s.alpha, 0.05), 1)
        s.Ve += DVe
        s.Vi += DVi

        s.assoc = s.Ve - s.Vi

class RescorlaWagnerExponential(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        if sign == 1:
            s.alpha *= (s.alpha ** 0.05) ** sign
        s.assoc += s.alpha * self.delta_v_factor

class Mack(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        s.alpha_mack = self.get_alpha_mack(s, sigma)
        s.alpha = s.alpha_mack
        s.assoc = s.assoc * self.delta_v_factor + self.delta_v_factor/2*beta

class Hall(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        s.alpha_hall = self.get_alpha_hall(s, sigma, self.prev_lamda)
        s.alpha = s.alpha_hall
        self.delta_v_factor = 0.5 * abs(self.prev_lamda)
        s.assoc += s.alpha * beta * (lamda - sigma)

class Macknhall(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        s.alpha_mack = self.get_alpha_mack(s, sigma)
        s.alpha_hall = self.get_alpha_hall(s, sigma, self.prev_lamda)
        s.alpha = (1 - abs(self.prev_lamda - sigma)) * s.alpha_mack + s.alpha_hall
        s.assoc += s.alpha * self.delta_v_factor

class NewDualV(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        rho = lamda - (sigmaE - sigmaI)

        delta_ma_hall = s.delta_ma_hall or 0
        self.gamma = 1 - math.exp(-delta_ma_hall**2)

        if rho >= 0:
            s.Ve += self.betap * s.alpha * lamda
        else:
            s.Vi += self.betan * s.alpha * abs(rho)

        s.alpha = self.gamma * abs(rho) + (1 - self.gamma) * s.alpha
        s.assoc = s.Ve - s.Vi

class Dualmack(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        rho = lamda - (sigmaE - sigmaI)

        VXe = sigmaE - s.Ve
        VXi = sigmaI - s.Vi

        if rho >= 0:
            s.Ve += s.alpha * self.betap * (1 - s.Ve + s.Vi) * abs(rho)
        else:
            s.Vi += s.alpha * self.betan * (1 - s.Vi + s.Ve) * abs(rho)

        s.alpha = 1/2 * (1 + s.assoc - (VXe - VXi))
        s.assoc = s.Ve - s.Vi

class Hybrid(AdaptiveType):
    def step(self, s: Stimulus, beta: float, lamda: float, sign: int, sigma: float, sigmaE: float, sigmaI: float):
        rho = lamda - (sigmaE - sigmaI)

        NVe = 0.
        NVi = 0.
        if rho >= 0:
            DVe = s.alpha_hall * self.betap * (1 - s.Ve + s.Vi) * abs(rho)
            NVe = s.Ve + DVe
            NVi = s.Vi
        else:
            NVe = s.Ve
            DvI = s.alpha_hall * self.betan * (1 - s.Vi + s.Ve) * abs(rho)
            NVi = s.Vi + DvI

        VXe = sigmaE - s.Ve
        VXi = sigmaI - s.Vi
        if rho > 0:
            s.alpha_mack += -self.thetaE * (abs(lamda - s.Ve + s.Vi) - abs(lamda - VXe + VXi))
        elif rho < 0:
            s.alpha_mack += -self.thetaI * (abs(abs(rho) - s.Vi + s.Ve) - abs(abs(rho) - VXi + VXe))

        s.alpha_mack = min(max(s.alpha_mack, 0.05), 1)
        s.alpha_hall = self.gamma * abs(rho) + (1 - self.gamma) * s.alpha_hall

        s.Ve = NVe
        s.Vi = NVi

        s.assoc = s.alpha_mack * (s.Ve - s.Vi)
