import random
import re
from dataclasses import dataclass

from Group import Group
from Strengths import Strengths, History

class Phase:
    # elems contains a list of ([CS], US) of an experiment.
    elems : list[tuple[str, str]]

    # Whether this phase should be randomised.
    rand : bool

    # The lamda for this phase.
    lamda : None | float

    # String description of this phase.
    phase_str : str

    # Return the set of single (one-character) CS.
    def cs(self):
        return set.union(*[set(x[0]) for x in self.elems])

    def __init__(self, phase_str : str):
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

    use_configurals: bool
    adaptive_type: str
    window_size: int
    xi_hall: float
    num_trials: int

    # TODO: Change this to default_alpha or something like that
    alpha: float

    plot_phase: None | int = None
    plot_experiments: None | list[str] = None
    plot_stimuli: None | list[str] = None
    plot_alpha: bool = False
    plot_macknhall: bool = False

    title_suffix: None | str = None
    savefig: None | str = None

def create_group_and_phase(name: str, phase_strs: list[str], args) -> tuple[Group, list[Phase]]:
    phases = [Phase(phase_str) for phase_str in phase_strs]

    stimuli = set.union(*[x.cs() for x in phases])
    g = Group(
        name = name,
        alphas = args.alphas,
        default_alpha = args.alpha,
        betan = args.beta_neg,
        betap = args.beta,
        lamda = args.lamda,
        gamma = args.gamma,
        thetaE = args.thetaE,
        thetaI = args.thetaI,
        cs = stimuli,
        use_configurals = args.use_configurals,
        adaptive_type = args.adaptive_type,
        window_size = args.window_size,
        xi_hall = args.xi_hall,
    )

    return g, phases

def run_group_experiments(g : Group, experiment : list[Phase], num_trials : int) -> list[list[Strengths]]:
    results = []

    for trial, phase in enumerate(experiment):
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
                Strengths.avg([h[x] for h in hist if x < len(h)])
                for x in range(max(len(h) for h in hist))
            ])

            g.s = Strengths.avg(final_strengths)

    return results

def group_results(results: list[list[Strengths]], name: str, args: RWArgs) -> list[dict[str, History]]:
    group_strengths = [History.emptydict() for _ in results]
    for phase_num, strength_hist in enumerate(results):
        for strengths in strength_hist:
            for cs in strengths.ordered_cs():
                if args.plot_stimuli is None or cs in args.plot_stimuli:
                    group_strengths[phase_num][f'{name} - {cs}'].add(strengths[cs])

    return group_strengths
