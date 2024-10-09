import random
import re
from dataclasses import dataclass

from Group import Group
from Environment import Environment, StimulusHistory

class Phase:
    # elems contains a list of ([CS], US) of an experiment.
    elems: list[tuple[str, str]]

    # Whether this phase should be randomised.
    rand: bool

    # The lamda for this phase.
    lamda: None | float

    # String description of this phase.
    phase_str: str

    # Return the set of single (one-character) CS.
    def cs(self):
        return set.union(*[set(x[0]) for x in self.elems])

    def __init__(self, phase_str: str):
        self.phase_str = phase_str
        self.rand = False
        self.lamda = None
        self.elems = []

        for part in phase_str.strip().split('/'):
            if part == 'rand':
                self.rand = True
            elif (match := re.fullmatch(r'lamb?da *= *([0-9]*(?:\.[0-9]*)?)', part)) is not None:
                self.lamda = float(match.group(1))
            elif (match := re.fullmatch(r'([0-9]*)([A-Z]+)([+-]?)', part)) is not None:
                num, cs, sign = match.groups()
                self.elems += int(num or '1') * [(cs, sign or '+')]
            else:
                raise ValueError(f'Part not understood: {part}')

@dataclass(kw_only = True)
class RWArgs:
    alphas: dict[str, float]
    beta: float
    beta_neg: float
    lamda: float
    gamma: float
    thetaE: float
    thetaI: float

    adaptive_type: str
    window_size: int
    xi_hall: float
    num_trials: int

    # TODO: Change this to default_alpha or something like that
    alpha: float
    alpha_mack: None | float = None
    alpha_hall: None | float = None

    plot_phase: None | int = None
    plot_experiments: None | list[str] = None
    plot_stimuli: None | list[str] = None
    plot_alpha: bool = False
    plot_macknhall: bool = False

    title_suffix: None | str = None
    savefig: None | str = None

class Experiment:
    name: str
    phases: list[Phase]

    def __init__(self, name: str, phase_strs: list[str]):
        self.name = name
        self.phases = [Phase(phase_str) for phase_str in phase_strs]

    def run_all_phases(self, args: RWArgs) -> list[dict[str, StimulusHistory]]:
        group = self.initial_group(args)
        results = self.run_group_experiments(group, args.num_trials)
        strengths = self.group_results(results, args)

        return strengths

    def initial_group(self, args: RWArgs) -> Group:
        stimuli = set.union(*[x.cs() for x in self.phases])
        g = Group(
            name = self.name,
            alphas = args.alphas,
            default_alpha = args.alpha,
            default_alpha_mack = args.alpha_mack,
            default_alpha_hall = args.alpha_hall,
            betan = args.beta_neg,
            betap = args.beta,
            lamda = args.lamda,
            gamma = args.gamma,
            thetaE = args.thetaE,
            thetaI = args.thetaI,
            cs = stimuli,
            adaptive_type = args.adaptive_type,
            window_size = args.window_size,
            xi_hall = args.xi_hall,
        )

        return g

    def run_group_experiments(self, g: Group, num_trials: int) -> list[list[Environment]]:
        results = []

        for trial, phase in enumerate(self.phases):
            if not phase.rand:
                strength_hist = g.runPhase(phase.elems, phase.lamda)
                results.append(strength_hist)
            else:
                initial_strengths = g.s.copy()
                final_strengths = []
                hist = []

                for trial in range(num_trials):
                    random.shuffle(phase.elems)

                    g.s = initial_strengths.copy()
                    hist.append(g.runPhase(phase.elems, phase.lamda))
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
                for cs in strengths.ordered_cs():
                    if args.plot_stimuli is None or cs in args.plot_stimuli:
                        group_strengths[phase_num][f'{self.name} - {cs}'].add(strengths[cs])

        return group_strengths
