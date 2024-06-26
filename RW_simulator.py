import argparse
import random
import re
import sys
from collections import defaultdict
from matplotlib.ticker import StrMethodFormatter, MaxNLocator
from RW_experiment import run_stuff
from RW_group import Group
from RW_strengths import Strengths, History
from RW_plots import plot_graphs

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Behold! My Rescorla-Wagnerinator!",
        epilog = '--alpha_[A-Z] ALPHA\tAssociative strength of CS A..Z. By default 0',
    )

    parser.add_argument('--alpha', type = float, default = .1, help = 'Alpha for all other stimuli')
    parser.add_argument("--beta", type = float, default = .3, help="Associativity of the US +.")
    parser.add_argument("--beta-neg", type = float, default = .2, help="Associativity of the absence of US +. Equal to beta by default.")
    parser.add_argument("--lamda", type = float, default = 1, help="Asymptote of learning.")
    parser.add_argument("--gamma", type = float, default = .5, help = "Weighting how much you rely on past experinces on DualV adaptive type.")

    parser.add_argument("--thetaE", type = float, default = .3, help = "Theta for excitatory phenomena in LePelley blocking")
    parser.add_argument("--thetaI", type = float, default = .1, help = "Theta for inhibitory phenomena in LePelley blocking")

    parser.add_argument("--use-configurals", type = bool, action = argparse.BooleanOptionalAction, help = 'Use compound stimuli with configural cues')

    parser.add_argument("--adaptive-type", choices = ['linear', 'exponential', 'mack', 'hall', 'macknhall', 'dualV', 'lepelley', 'dualmack', 'hybrid'], default = 'dualV', help = 'Type of adaptive attention mode to use')
    parser.add_argument("--window-size", type = int, default = None, help = 'Size of sliding window for adaptive learning')

    parser.add_argument("--xi-hall", type = float, default = 0.2, help = 'Xi parameter for Hall alpha calculation')

    parser.add_argument("--num-trials", type = int, default = 1000, help = 'Amount of trials done in randomised phases')

    parser.add_argument('--plot-phase', type = int, help = 'Plot a single phase')
    parser.add_argument("--plot-experiments", nargs = '*', help = 'List of experiments to plot. By default plot everything')
    parser.add_argument("--plot-stimuli", nargs = '*', help = 'List of stimuli, compound and simple, to plot. By default plot everything')
    parser.add_argument('--plot-alphas', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot all the alphas, including total alpha, alpha Mack, and alpha Hall.')

    parser.add_argument('--plot-alpha', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot the total alpha.')
    parser.add_argument('--plot-macknhall', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot the alpha Mack and alpha Hall.')

    parser.add_argument('--title-suffix', type = str, help = 'Title suffix')

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

    if args.use_configurals is None:
        args.use_configurals = False

    args.use_adaptive = args.adaptive_type is not None

    if args.adaptive_type.endswith('hall') and args.window_size is None:
        args.window_size = 3

    if args.plot_alphas:
        args.plot_alpha = True
        args.plot_macknhall = True

    return args

def main():
    args = parse_args()

    groups_strengths = None

    # phases: dict[str, list[Phase]] = dict()
    for e, experiment in enumerate(args.experiment_file.readlines()):
        name, *phase_strs = experiment.strip().split('|')
        name = name.strip()

        if groups_strengths is None:
            groups_strengths = [History.emptydict() for _ in phase_strs]

        if args.plot_experiments is not None and name not in args.plot_experiments:
            continue

        # if name in phases:
            # raise NameError(f'Repeated phase name {name}')

        local_strengths = run_stuff(name, phase_strs, args)
        groups_strengths = [a | b for a, b in zip(groups_strengths, local_strengths)]

    assert(groups_strengths is not None)
    plot_graphs(
        groups_strengths,
        # phases = phases,
        filename = args.savefig,
        plot_phase = args.plot_phase,
        plot_alpha = args.plot_alpha,
        plot_macknhall = args.plot_macknhall,
        title_suffix = args.title_suffix
    )

if __name__ == '__main__':
    main()
