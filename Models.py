# This file defines all models used in the simulator.
# Instructions to add a new model are found in the "Adding new Models" section of the paper.
# The models in the simulator are contained in the return dictionary of the
# `types` classmethod in the Model class.

from __future__ import annotations
from dataclasses import dataclass

import math
from typing import Type, ClassVar

from Environment import Stimulus

@dataclass
class RunParameters:
    beta: float
    lamda: float
    sign: int
    sigma: float
    sigmaE: float
    sigmaI: float
    count: float
    maxAssocRest: float
    trial_num: int

# Base class for all models. New models can be added by sub-classing this
# class, and defining an overloaded `step` method.
class Model:
    image_filename: ClassVar[str] = ''

    betan: float
    betap: float
    lamda: float
    xi_hall: None | float
    gamma: float
    thetaE: float
    thetaI: float
    kay: float

    # `types` contains the active models in the simulator.
    # Adding a new name/Model pair to this dictionary here will
    # automatically add this to the next run of the simulator,
    # without requiring any other change.
    # The model must have a `step` function at minimum.
    @classmethod
    def types(cls) -> dict[str, Type[Model]]:
        return {
            'Rescorla Wagner': RescorlaWagner,
            'Pearce Kaye Hall': PearceKayeHall,
            'Mackintosh Extended': MackExtended,
            'Le Pelley\'s Hybrid': LePelleyHybrid,
            'MLAB Model': MLABModel,
        }

    # Run a step of a certain adaptive type. This is the only function that
    # requires being overloaded by subclasses of Model.
    # Arguments:
    #   s: Stimulus, definition of the stimulus at a certain point (see Environment.py).
    #      This parameter must be modified by the class.
    #  rp: RunPArameters, parameters passed to the model.
    def step(self, s: Stimulus, rp: RunParameters):
        raise NotImplementedError('Step method not overloaded.')

    # List of parameters enabled by this model. Parameters not enabled will
    # be marked as gray on the GUI.
    # By default, enable all parameters.
    @classmethod
    def parameters(cls) -> list[str]:
        return [
            'alpha',
            'alpha_mack',
            'alpha_hall',
            'beta',
            'betan',
            'lamda',
            'gamma',
            'thetaE',
            'thetaI',
            'salience',
        ]

    # Dictionary of default values for certain parameters.
    # If these parameters are not changed manually, then when changing
    # to this model the parameter in each key will take the form of the value.
    @classmethod
    def defaults(cls) -> dict[str, float]:
        return {}

    # Dictionary of bounds for certain parameters.
    # If a parameter is here, the GUI will warn when its value is outside
    # the [min, max] bounds returned by this function.
    @classmethod
    def bounds(cls) -> dict[str, tuple[float, float]]:
        return {}

    # Private method of Models; these should not be overloaded by subclasses.
    def __init__(self, betan: float, betap: float, lamda: float, xi_hall: None | float, gamma: float, thetaE: float, thetaI: float, kay: float):
        self.betan = betan
        self.betap = betap
        self.lamda = lamda
        self.xi_hall = xi_hall
        self.gamma = gamma
        self.thetaE = thetaE
        self.thetaI = thetaI
        self.kay = kay

    @classmethod
    def base(cls, model_name) -> Type[Model]:
        return cls.types()[model_name]

    @classmethod
    def get(cls, model_name, *args, **kwargs) -> Model:
        return cls.base(model_name)(*args, **kwargs)

    @classmethod
    def should_plot_macknhall(cls) -> bool:
        return 'alpha_mack' in cls.parameters() and 'alpha_hall' in cls.parameters()

    @classmethod
    def initial_defaults(cls) -> dict[str, float]:
        inits = dict(
            alpha = 0.5,
            alpha_mack = 0.5,
            alpha_hall = 0.5,
            salience = 0.5,
            habituation = 0.99,
            lamda = 1,
            beta = 0.3,
            betan = 0.2,
            gamma = 0.15,
            thetaE = 0.3,
            thetaI = 0.1,
            rho = 0.2,
            nu = 0.25,
            kay = 2,
            num_trials = 100,
        )

        return {k: v for k, v in inits.items() if k in {'num_trials'} | set(cls.parameters())}

    def get_alpha_mack(self, s: Stimulus, sigma: float) -> float:
        return 1/2 * (1 + 2*s.assoc - sigma)

    def get_alpha_hall(self, s: Stimulus, sigma: float, lamda: float) -> float:
        assert self.xi_hall is not None

        surprise = abs(lamda - sigma)
        gamma = 0.99
        kayes = gamma*surprise +  (1-gamma)*s.alpha_hall

        new_error = kayes

        return new_error

    def run_step(self, s: Stimulus, rp: RunParameters):
        assert rp.maxAssocRest != -1

        self.delta_v_factor = rp.beta * (rp.lamda - rp.sigma)
        try:
            self.step(s, rp)
        except OverflowError:
            print(f'{rp.lamda=}\t{rp.sigma=}')
            raise

        for prop, (lower, upper) in self.bounds().items():
            setattr(s, prop, min(upper, max(lower, getattr(s, prop))))

class RescorlaWagner(Model):
    image_filename: ClassVar[str] = 'RW.png'

    @classmethod
    def parameters(cls) -> list[str]:
        return ['alpha', 'beta', 'betan', 'lamda']

    @classmethod
    def defaults(cls) -> dict[str, float]:
        return dict(
            alpha = .2,
            beta = .5,
            betan = .4,
        )

    def step(self, s: Stimulus, rp: RunParameters):
        s.assoc += s.alpha * self.delta_v_factor

class PearceKayeHall(Model):
    image_filename: ClassVar[str] = 'PKH.png'

    @classmethod
    def parameters(cls) -> list[str]:
        return ['alpha', 'beta', 'betan', 'lamda', 'gamma', 'salience']

    @classmethod
    def defaults(cls) -> dict[str, float]:
        return dict(
            alpha = .9,
            salience = .2,
            beta = .3,
            betan = .1,
            gamma = .2,
            lamda = .8,
        )

    def step(self, s: Stimulus, rp: RunParameters):
        rho = rp.lamda - (rp.sigmaE - rp.sigmaI)

        if rho >= 0:
            s.Ve += rp.beta * s.alpha * rp.lamda * s.salience
        else:
            s.Vi += self.betan * s.alpha * abs(rho) * s.salience

        s.alpha = self.gamma * abs(rho) + (1 - self.gamma) * s.alpha
        s.assoc = s.Ve - s.Vi

class MackExtended(Model):
    image_filename: ClassVar[str] = 'Extended_Mack.png'

    @classmethod
    def parameters(cls) -> list[str]:
        return ['alpha', 'beta', 'betan', 'lamda', 'thetaE', 'thetaI']

    @classmethod
    def defaults(cls) -> dict[str, float]:
        return dict(
            alpha = .9,
            beta = .3,
            betan = .1,
            thetaE = .3,
            thetaI = .1,
            lamda = .8,
        )

    def step(self, s: Stimulus, rp: RunParameters):
        rho = rp.lamda - (rp.sigmaE - rp.sigmaI)
        betap = rp.beta if rp.sign == 1 else self.betap

        # LomE and LomI are \Lambda and \overline{\Lambda} in the formulas.
        LomE = rp.sigmaE - s.Ve
        LomI = rp.sigmaI - s.Vi

        DVe = 0.
        DVi = 0.
        if rho > 0:
            DVe = s.alpha * betap * (1 - s.Ve + s.Vi) * abs(rho)
            s.alpha += -self.thetaE * (abs(rp.lamda - s.Ve + s.Vi) - abs(rp.lamda - LomE + LomI))
        elif rho < 0:
            DVi = s.alpha * self.betan * (1 - s.Vi + s.Ve) * abs(rho)
            s.alpha += -self.thetaI * (abs(abs(rho) - s.Vi + s.Ve) - abs(abs(rho) - LomI + LomE))

        s.alpha = min(max(s.alpha, 0.05), 1)

        s.Ve += DVe
        s.Vi += DVi
        s.assoc = s.Ve - s.Vi

class LePelleyHybrid(Model):
    image_filename: ClassVar[str] = 'LePelley.png'

    @classmethod
    def parameters(cls) -> list[str]:
        return ['alpha_mack', 'alpha_hall', 'beta', 'betan', 'lamda', 'gamma', 'thetaE', 'thetaI']

    @classmethod
    def defaults(cls) -> dict[str, float]:
        return dict(
            alpha_mack = .9,
            alpha_hall = .9,
            beta = .3,
            betan = .1,
            thetaE = .3,
            thetaI = .1,
            lamda = .8,
        )

    @classmethod
    def bounds(cls) -> dict[str, tuple[float, float]]:
        return dict(
            alpha_mack = (0.05, 1),
            alpha_hall = (0.5 , 1),
        )

    def step(self, s: Stimulus, rp: RunParameters):
        # Ignore likely dummy stimuli
        if s.assoc == 0 and s.alpha_mack == 0 and s.alpha_hall == 0:
            return

        rho = rp.lamda - (rp.sigmaE - rp.sigmaI)

        VXe = rp.sigmaE - s.Ve
        VXi = rp.sigmaI - s.Vi

        betap = rp.beta if rp.sign == 1 else self.betap

        DVe = 0.
        DVi = 0.
        if rho >= 0:
            DVe = s.alpha_mack * s.alpha_hall * betap * (1 - s.Ve + s.Vi) * abs(rho)

            if rho > 0:
                s.alpha_mack += -self.thetaE * (abs(rp.lamda - s.Ve + s.Vi) - abs(rp.lamda - VXe + VXi))
        else:
            DVi = s.alpha_mack * s.alpha_hall * self.betan * (1 - s.Vi + s.Ve) * abs(rho)
            s.alpha_mack += -self.thetaI * (abs(abs(rho) - s.Vi + s.Ve) - abs(abs(rho) - VXi + VXe))

        s.alpha_hall = self.gamma * (rp.lamda - rp.sigma) + (1 - self.gamma) * s.alpha_hall
        s.alpha_mack = min(max(s.alpha_mack, 0.05), 1)
        s.alpha_hall = min(max(s.alpha_hall, 0.5), 1)

        s.Ve += DVe
        s.Vi += DVi
        s.assoc = s.Ve - s.Vi

class MlabHybrid(Model):
    @classmethod
    def parameters(cls) -> list[str]:
        return ['alpha','salience', 'habituation', 'lamda','rho', 'nu', 'kay']

    @classmethod
    def defaults(cls) -> dict[str, float]:
        return dict(
            alpha = 0.5,
            salience = .1,
            habituation = 1,
            lamda = 1,
            rho = 0.5,
            nu = 0.5,
            kay = 0.005,
        )

    def step(self, s: Stimulus, rp: RunParameters):
        s.habituation = s.habituation * math.exp(-self.kay * s.salience)
        DV = s.alpha * s.salience * (rp.lamda - rp.sigma)
        s.alpha = (1-s.habituation) * (rp.lamda - rp.sigma)**2 * (s.nu + s.rho * ((rp.sigma - s.assoc) + (rp.sigma - rp.maxAssocRest))) + s.habituation * s.alpha

        s.assoc = s.assoc + DV

class MLABModel(Model):
    image_filename: ClassVar[str] = 'RW-Linear.png'

    @classmethod
    def parameters(cls) -> list[str]:
        return ['alpha', 'beta', 'betan', 'lamda']

    @classmethod
    def defaults(cls) -> dict[str, float]:
        return dict(
            alpha = .2,
            beta = .5,
            betan = .4,
        )

    def step(self, s: Stimulus, rp: RunParameters):
        d = 0.05

        if rp.lamda > 0:
            s.alpha = s.alpha * (1 - d) + s.alpha_0 * s.assoc * (rp.lamda - rp.sigma)
        else:
            s.alpha = s.alpha * (1 - d) - s.alpha_0 * s.assoc * (rp.lamda - rp.sigma)

        s.alpha = min(max(s.alpha, 0.05), 1)
        s.assoc += s.alpha * self.delta_v_factor

# Extra models, not used in the simulator.
# These can be added by adding an extra line to the `types` class method in the `Model` class.
class Mack(Model):
    @classmethod
    def parameters(cls) -> list[str]:
        return ['alpha', 'beta', 'betan', 'lamda']

    def step(self, s: Stimulus, rp: RunParameters):
        s.alpha_mack = self.get_alpha_mack(s, rp.sigma)
        s.alpha = s.alpha_mack
        s.assoc = s.assoc * self.delta_v_factor + self.delta_v_factor/2*rp.beta

class Hall(Model):
    @classmethod
    def parameters(cls) -> list[str]:
        return ['alpha', 'beta', 'betan', 'lamda']

    def step(self, s: Stimulus, rp: RunParameters):
        s.alpha_hall = self.get_alpha_hall(s, rp.sigma, rp.lamda)
        s.alpha = s.alpha_hall
        self.delta_v_factor = 0.5 * abs(rp.lamda)
        s.assoc += s.alpha * rp.beta * (rp.lamda - rp.sigma)

class Macknhall(Model):
    @classmethod
    def parameters(cls) -> list[str]:
        return ['alpha', 'beta', 'betan', 'lamda']

    def step(self, s: Stimulus, rp: RunParameters):
        s.alpha_mack = self.get_alpha_mack(s, rp.sigma)
        s.alpha_hall = self.get_alpha_hall(s, rp.sigma, rp.lamda)
        s.alpha = (1 - abs(rp.lamda - rp.sigma)) * s.alpha_mack + s.alpha_hall
        s.assoc += s.alpha * self.delta_v_factor

class Dualmack(Model):
    @classmethod
    def parameters(cls) -> list[str]:
        return ['alpha', 'beta', 'betan', 'lamda']

    def step(self, s: Stimulus, rp: RunParameters):
        rho = rp.lamda - (rp.sigmaE - rp.sigmaI)

        VXe = rp.sigmaE - s.Ve
        VXi = rp.sigmaI - s.Vi

        if rho >= 0:
            s.Ve += s.alpha * self.betap * (1 - s.Ve + s.Vi) * abs(rho)
        else:
            s.Vi += s.alpha * self.betan * (1 - s.Vi + s.Ve) * abs(rho)

        s.alpha = 1/2 * (1 + s.assoc - (VXe - VXi))
        s.assoc = s.Ve - s.Vi

class OldHybrid(Model):
    @classmethod
    def parameters(cls) -> list[str]:
        return ['alpha', 'beta', 'betan', 'lamda', 'alpha_mack', 'alpha_hall', 'thetaE', 'thetaI', 'gamma']

    def step(self, s: Stimulus, rp: RunParameters):
        rho = rp.lamda - (rp.sigmaE - rp.sigmaI)

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

        VXe = rp.sigmaE - s.Ve
        VXi = rp.sigmaI - s.Vi
        if rho > 0:
            s.alpha_mack += -self.thetaE * (abs(rp.lamda - s.Ve + s.Vi) - abs(rp.lamda - VXe + VXi))
        elif rho < 0:
            s.alpha_mack += -self.thetaI * (abs(abs(rho) - s.Vi + s.Ve) - abs(abs(rho) - VXi + VXe))

        s.alpha_mack = min(max(s.alpha_mack, 0.05), 1)
        s.alpha_hall = self.gamma * abs(rho) + (1 - self.gamma) * s.alpha_hall

        s.Ve = NVe
        s.Vi = NVi

        s.assoc = s.alpha_mack * (s.Ve - s.Vi)

