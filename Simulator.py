import argparse
import random
import re
import sys
from collections import defaultdict
from Experiment import Experiment, Phase
from Group import Group
from Environment import Environment, StimulusHistory
from Plots import show_plots, save_plots
from AdaptiveType import AdaptiveType

# Given a list of arguments, matches the ones corresponding to a particular name
# combined with a CS and returns them as a dictionary, along with the remaining
# arguments.
def match_args(name: str, args: list[str]) -> tuple[dict[str, float], list[str]]:
    values = dict()
    rest = list()

    for arg in args:
        match = re.fullmatch(rf'--{name}[-_]([A-Z])\s*=?\s*([0-9]*\.?[0-9]*)', arg)
        if match:
            values[match.group(1)] = float(match.group(2))
        else:
            rest.append(arg)

    return values, rest

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Behold! My Rescorla-Wagnerinator!",
        epilog = '--alpha_[A-Z] ALPHA\tAssociative strength of CS A..Z. By default 0',
    )

    parser.add_argument("--adaptive-type", choices = AdaptiveType.types().keys(), default = 'rescorla_wagner', help = 'Type of adaptive attention mode to use')

    parser.add_argument('--alpha', type = float, default = .1, help = 'Alpha for all other stimuli')
    parser.add_argument('--alpha-mack', type = float, help = 'Alpha_mack for all other stimuli')
    parser.add_argument('--alpha-hall', type = float, help = 'Alpha_hall for all other stimuli')

    parser.add_argument("--beta", type = float, default = .3, help="Associativity of the US +.")
    parser.add_argument("--beta-neg", type = float, default = .2, help="Associativity of the absence of US +. Equal to beta by default.")
    parser.add_argument("--lamda", type = float, default = 1, help="Asymptote of learning.")
    parser.add_argument("--gamma", type = float, default = .5, help = "Weighting how much you rely on past experinces on DualV adaptive type.")

    parser.add_argument("--thetaE", type = float, default = .2, help = "Theta for excitatory phenomena in LePelley blocking")
    parser.add_argument("--thetaI", type = float, default = .1, help = "Theta for inhibitory phenomena in LePelley blocking")

    parser.add_argument("--window-size", type = int, default = None, help = 'Size of sliding window for adaptive learning')

    parser.add_argument('--salience', type = float, default = .5, help = 'Salience for all parameters without an individually defined salience. This is used in the Pearce & Hall model.')
    parser.add_argument('--habituation', type = float, default = .99, help = 'Habituation delay for all parameters in the hybrid model.')

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

    # Accept parameters for alphas and saliences
    args, rest = parser.parse_known_args()
    args.alphas, rest = match_args('alpha', rest)
    args.saliences, rest = match_args('salience', rest)
    if rest:
        raise KeyError(f"Arguments not recognised: {' '.join(rest)}.")

    args.use_adaptive = args.adaptive_type is not None

    if args.adaptive_type.endswith('hall') and args.window_size is None:
        args.window_size = 3

    if args.plot_alphas:
        args.plot_alpha = True
        args.plot_macknhall = True

    return args

def main() -> None:
    args = parse_args()

    groups_strengths = None

    phases: dict[str, list[Phase]] = dict()
    for e, experiment in enumerate(args.experiment_file.readlines()):
        name, *phase_strs = experiment.strip().split('|')
        name = name.strip()

        if groups_strengths is None:
            groups_strengths = [StimulusHistory.emptydict() for _ in phase_strs]

        if args.plot_experiments is not None and name not in args.plot_experiments:
            continue

        experiment = Experiment(name, phase_strs)
        local_strengths = experiment.run_all_phases(args)
        groups_strengths = [a | b for a, b in zip(groups_strengths, local_strengths)]
        phases[name] = experiment.phases

    assert(groups_strengths is not None)

    if args.savefig is None:
        show_plots(
            groups_strengths,
            phases = phases,
            plot_phase = args.plot_phase,
            plot_alpha = args.plot_alpha,
            plot_macknhall = args.plot_macknhall,
        )
        input('Press any key to continue...')
    else:
        save_plots(
            groups_strengths,
            phases = phases,
            filename = args.savefig,
            plot_phase = args.plot_phase,
            plot_alpha = args.plot_alpha,
            plot_macknhall = args.plot_macknhall,
            title_suffix = args.title_suffix
        )

if __name__ == '__main__':
    main()
