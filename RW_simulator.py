import argparse
import random
import re
import sys
from collections import defaultdict
from matplotlib.ticker import StrMethodFormatter, MaxNLocator
from RW_group import Group
from RW_strengths import Strengths, History
from RW_plots import plot_graphs

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Behold! My Rescorla-Wagnerinator!",
        epilog = '--alpha_[A-Z] ALPHA\tAssociative strength of CS A..Z. By default 0',
    )

    parser.add_argument("--beta", type = float, default = .5, help="Associativity of the US +.")
    parser.add_argument("--beta-neg", type = float, default = None, help="Associativity of the absence of US +. Equal to beta by default.")
    parser.add_argument("--lamda", type = float, default = 1, help="Asymptote of learning.")
    parser.add_argument("--gamma", type = float, default = .5, help = "Weighting how much you rely on past experinces on DualV adaptive type.")

    parser.add_argument("--thetaE", type = float, default = .3, help = "Theta for excitatory phenomena in LePelley blocking")
    parser.add_argument("--thetaI", type = float, default = .1, help = "Theta for inhibitory phenomena in LePelley blocking")

    parser.add_argument("--use-configurals", type = bool, action = argparse.BooleanOptionalAction, help = 'Use compound stimuli with configural cues')

    parser.add_argument("--adaptive-type", choices = ['linear', 'exponential', 'mack', 'hall', 'macknhall', 'dualV', 'lepelley'], default = 'dualV', help = 'Type of adaptive attention mode to use')
    parser.add_argument("--window-size", type = int, default = None, help = 'Size of sliding window for adaptive learning')

    parser.add_argument("--xi-hall", type = float, default = 0.2, help = 'Xi parameter for Hall alpha calculation')

    parser.add_argument("--num-trials", type = int, default = 1000, help = 'Amount of trials done in randomised phases')

    parser.add_argument('--plot-phase', type = int, help = 'Plot a single phase')
    parser.add_argument("--plot-experiments", nargs = '*', help = 'List of experiments to plot. By default plot everything')
    parser.add_argument("--plot-stimuli", nargs = '*', help = 'List of stimuli, compound and simple, to plot. By default plot everything')
    parser.add_argument('--plot-alphas', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot all the alphas, including total alpha, alpha Mack, and alpha Hall.')

    parser.add_argument('--plot-alpha', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot the total alpha.')
    parser.add_argument('--plot-macknhall', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot the alpha Mack and alpha Hall.')

    parser.add_argument('--savefig', type = str, help = 'Instead of showing figures, they will be saved to "fig_n.png"')

    parser.add_argument(
        "experiment_file",
        nargs='?',
        type = argparse.FileType('r'),
        default = sys.stdin,
        help="Path to the experiment file."
    )

    # Also accept arguments of the form --alpha_[A-Z]=n.
    args, rest = parser.parse_known_args()
    args.alphas = dict()
    for arg in rest:
        match = re.fullmatch(r'--alpha[-_]([A-Z])\s*=?\s*([0-9]*\.?[0-9]*)', arg)
        if not match:
            parser.error(f'Option not understood: {arg}')

        args.alphas[match.group(1)] = float(match.group(2))

    if args.beta_neg is None:
        args.beta_neg = args.beta

    if args.use_configurals is None:
        args.use_configurals = False

    args.use_adaptive = args.adaptive_type is not None

    if args.adaptive_type.endswith('hall') and args.window_size is None:
        args.window_size = 3

    if args.plot_alphas:
        args.plot_alpha = True
        args.plot_macknhall = True

    return args

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

def main():
    args = parse_args()

    groups_strengths = []

    phases: dict[str, list[Phase]] = dict()
    for e, experiment in enumerate(args.experiment_file.readlines()):
        name, *phase_strs = experiment.strip().split('|')
        name = name.strip()

        if args.plot_experiments is not None and name not in args.plot_experiments:
            continue

        if name in phases:
            raise NameError(f'Repeated phase name {name}')

        phases[name] = [Phase(phase_str) for phase_str in phase_strs]

        cs = set.union(*[x.cs() for x in phases[name]])
        g = Group(
            name = name,
            alphas = args.alphas,
            betan = args.beta_neg,
            betap = args.beta,
            lamda = args.lamda,
            gamma = args.gamma,
            thetaE = args.thetaE,
            thetaI = args.thetaI,
            cs = cs,
            use_configurals = args.use_configurals,
            adaptive_type = args.adaptive_type,
            window_size = args.window_size,
            xi_hall = args.xi_hall,
        )

        for phase_num, strength_hist in enumerate(run_group_experiments(g, phases[name], args.num_trials)):
            while len(groups_strengths) <= phase_num:
                groups_strengths.append(defaultdict(lambda: History()))

            for strengths in strength_hist:
                for cs in strengths.combined_cs():
                    if cs not in (args.plot_stimuli or [cs]):
                        continue

                    groups_strengths[phase_num][f'{name} - {cs}'].add(strengths[cs])

    plot_graphs(
        groups_strengths,
        phases = phases,
        filename = args.savefig,
        plot_phase = args.plot_phase,
        plot_alpha = args.plot_alpha,
        plot_macknhall = args.plot_macknhall,
        experiment_file = args.experiment_file.name,
    )

if __name__ == '__main__':
    main()
