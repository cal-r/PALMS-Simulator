from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import get_type_hints, get_args
from types import UnionType

from Group import Group
from Environment import Stimulus, Environment, StimulusHistory

class Phase:
    # elems contains a list of ([CS], US) of an experiment.
    elems: list[tuple[str, str]]

    # Whether this phase should be randomised.
    rand: bool

    # The beta for this phase if different to the environment.
    beta: None | float

    # The lamda for this phase if different to the enviroment.
    lamda: None | float

    # String description of this phase.
    phase_str: str

    # Return the set of single CS.
    def cs(self) -> set[str]:
        if not self.elems:
            return set()
        return set.union(*[set(Environment.list_cs(x[0])) for x in self.elems])

    # Return the list of applicable compound CS.
    # self.compound_cs() ⊇ self.cs()
    def compound_cs(self) -> list[str]:
        compound = {cs for cs, _ in self.elems}
        return sorted(compound, key = lambda x: (len(x.strip("'()")), x))

    def __init__(self, phase_str: str):
        self.phase_str = phase_str
        self.rand = False
        self.beta = None
        self.lamda = None
        self.elems = []

        for part in self.phase_str.strip().split('/'):
            if part == 'rand':
                self.rand = True
            elif (match := re.fullmatch(r"lamb?da *= *([0-9]*(?:\.[0-9]*)?)", part)) is not None:
                self.lamda = float(match.group(1))
            elif (match := re.fullmatch(r"beta *= *([0-9]*(?:\.[0-9]*)?)", part)) is not None:
                self.beta = float(match.group(1))
            elif (match := re.fullmatch(r"([0-9]*)((?:[A-Za-zÑñ]'*(?:\^[0-9]+)?)+)((?:\+\+|\+|\-)?)", part)) is not None:
                num, cs, sign = match.groups()
                cs = ''.join(Environment.split_cs(cs.upper()))
                self.elems += int(num or '1') * [(cs, sign or '+')]
            elif not part.strip():
                continue
            else:
                raise ValueError(f'Cannot parse this part: "{part}" of phase "{self.phase_str}"')

@dataclass
class RWArgs:
    def set_value(self, name: str, value: Any):
        prop_type = get_type_hints(self)[name]
        if isinstance(prop_type, UnionType):
            prop_type = next(t for t in get_args(prop_type) if t is not type(None))

        setattr(self, name, prop_type(value))

    adaptive_type: str

    alphas: dict[str, float]
    alpha_macks: dict[str, float]
    alpha_halls: dict[str, float]
    beta: float
    beta_neg: float
    lamda: float
    gamma: float
    thetaE: float
    thetaI: float

    xi_hall: float
    num_trials: int

    saliences: dict[str, float]
    salience: float

    habituations: dict[str, float]
    habituation: float
    rho: float
    nu: float
    kay: float

    # TODO: Change this to default_alpha or something like that
    alpha: float
    alpha_mack: None | float = None
    alpha_hall: None | float = None

    plot_phase: None | int = None
    plot_experiments: None | list[str] = None
    plot_stimuli: None | list[str] = None

    should_plot_macknhall: bool = False
    plot_alpha: bool = False
    plot_macknhall: bool = False

    title_suffix: None | str = None
    savefig: None | str = None

    configural_cues: bool = False
    part_stimuli: bool = False

class Experiment:
    name: str
    force_configural_cues: bool
    rest: list[str]
    phases: list[Phase]

    def __init__(self, name: str, phase_strs: list[str]):
        self.name, *rest = name.split('/')
        self.force_configural_cues = False
        for option in rest:
            if option == 'conf' or option == 'configural' or option == 'cc':
                self.force_configural_cues = True
            else:
                raise ValueError(f'Unknown option {option} on group {self.name}')

        self.phases = [Phase(phase_str) for phase_str in phase_strs]

    def run_all_phases(self, args: RWArgs) -> list[dict[str, StimulusHistory]]:
        # Set the static configural_cues variable for the entire environment.
        Environment.configural_cues = args.configural_cues

        # Easter egg: force configural cues on group with certain postfixes.
        reset_configural_cues = Environment.configural_cues
        if self.force_configural_cues:
            Environment.configural_cues = True

        group = self.initial_group(args)
        results = self.run_group_experiments(group, args.num_trials)
        strengths = self.group_results(results, args)

        Environment.configural_cues = reset_configural_cues

        return strengths

    def initial_group(self, args: RWArgs) -> Group:
        stimuli = set.union(*[x.cs() for x in self.phases])
        g = Group(
            name = self.name,
            alphas = args.alphas,
            default_alpha = args.alpha,
            alpha_macks = args.alpha_macks,
            default_alpha_mack = args.alpha_mack,
            alpha_halls = args.alpha_halls,
            default_alpha_hall = args.alpha_hall,
            saliences = args.saliences,
            default_salience = args.salience,
            habituations = args.habituations,
            default_habituation = args.habituation,
            rho = args.rho,
            nu = args.nu,
            kay = args.kay,
            betan = args.beta_neg,
            betap = args.beta,
            lamda = args.lamda,
            gamma = args.gamma,
            thetaE = args.thetaE,
            thetaI = args.thetaI,
            cs = stimuli,
            adaptive_type = args.adaptive_type,
            xi_hall = args.xi_hall,
        )

        return g

    def run_group_experiments(self, g: Group, num_trials: int) -> list[list[Environment]]:
        results = []

        for trial, phase in enumerate(self.phases):
            if not phase.rand:
                strength_hist = g.runPhase(phase.elems, phase.beta, phase.lamda)
                results.append(strength_hist)
            else:
                initial_strengths = g.s.copy()
                final_strengths = []
                hist = []

                for trial in range(num_trials):
                    random.shuffle(phase.elems)

                    g.s = initial_strengths.copy()
                    strength_hist = g.runPhase(phase.elems, phase.beta, phase.lamda)
                    hist.append(strength_hist)
                    final_strengths.append(g.s.copy())

                results.append([
                    Environment.avg([h[x] for h in hist if x < len(h)])
                    for x in range(max(len(h) for h in hist))
                ])

                g.s = Environment.avg(final_strengths)

        return results

    def group_results(self, results: list[list[Environment]], args: RWArgs) -> list[dict[str, StimulusHistory]]:
        group_strengths = [StimulusHistory.emptydict() for _ in results]
        for phase_num, strength_hist in enumerate(results):
            for strengths in strength_hist:
                for cs, stimulus in strengths.s.items():
                    if ('+' in cs or '-' in cs) and not args.part_stimuli:
                        continue

                    full_name = cs.replace('(', 'q(')
                    group_strengths[phase_num][f'{self.name} - {full_name}'].add(stimulus)

        return group_strengths
