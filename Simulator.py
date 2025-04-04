from __future__ import annotations

import argparse
import random
import re
import sys
from collections import defaultdict
from Experiment import Experiment, Phase, RWArgs
from Group import Group
from Environment import Environment, StimulusHistory
from Plots import generate_figures, save_plots
from AdaptiveType import AdaptiveType

import ipdb

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

def parse_args():
    parser = argparse.ArgumentParser(
        description="Behold! My Rescorla-Wagnerinator!",
        formatter_class = argparse.RawTextHelpFormatter,
        epilog = '''\
  --alpha-[A-Z] ALPHA\tAssociative strength of CS A..Z.
  --alpha_mack-[A-Z] ALPHA\n\t\t\tAssociative strength (Mackintosh) of CS A..Z.
  --alpha_hall-[A-Z] ALPHA\n\t\t\tAssociative strength (Hall) of CS A..Z.
  --saliences-[A-Z] SALIENCE\n\t\t\tSalience of CS A..Z.
  --habituations-[A-Z] HABITUATION\n\t\t\tHabituation of CS A..Z.
''',
    )

    parser.add_argument("--adaptive-type", choices = AdaptiveType.types().keys(), default = 'Rescorla Wagner', help = 'Type of adaptive attention mode to use')

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

    parser.add_argument("--num-trials", type = int, default = 100, help = 'Amount of trials done in randomised phases')

    parser.add_argument('--plot-phase', type = int, help = 'Plot a single phase')
    parser.add_argument("--plot-experiments", nargs = '*', help = 'List of experiments to plot. By default plot everything')
    parser.add_argument("--plot-stimuli", nargs = '*', help = 'List of stimuli, compound and simple, to plot. By default plot everything')
    parser.add_argument('--plot-alphas', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot all the alphas, including total alpha, alpha Mack, and alpha Hall.')

    parser.add_argument('--configural-cues', type = bool, default = False, action = argparse.BooleanOptionalAction, help = 'Whether to use configural cues')
    parser.add_argument('--rho', type = float, default = .1)
    parser.add_argument('--nu', type = float, default = .1)
    parser.add_argument('--kay', type = float, default = .1)

    parser.add_argument('--plot-alpha', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot the total alpha.')
    parser.add_argument('--plot-macknhall', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot the alpha Mack and alpha Hall.')

    parser.add_argument('--show-title', action = 'store_true', help = 'Show title and phases to saved plot.')
    parser.add_argument('--dpi', type = int, default = 200, help = 'Dots per inch.')
    parser.add_argument('--singular-legend', action = 'store_true', help = 'Hide legend in plot, and generate a separate file with all the legends together.')

    parser.add_argument('--savefig', type = str, help = 'Instead of showing figures, they will be saved to "fig_n.png"')

    parser.add_argument(
        "experiment_file",
        nargs='?',
        type = argparse.FileType('r'),
        default = sys.stdin,
        help="Path to the experiment file."
    )

    # Accept parameters for alphas, saliences, and habituations.
    args, rest = parser.parse_known_args()
    args.alphas, rest = match_args('alpha', rest)
    args.saliences, rest = match_args('salience', rest)
    args.habituations, rest = match_args('habituation', rest)
    args.alpha_macks, rest = match_args('alpha_mack', rest)
    args.alpha_halls, rest = match_args('alpha_hall', rest)
    if rest:
        raise KeyError(f"Arguments not recognised: {' '.join(rest)}.")

    args.use_adaptive = args.adaptive_type is not None

    if args.window_size is None:
        if args.adaptive_type.endswith('hall'):
            args.window_size = 3
        else:
            args.window_size = 1

    if args.plot_alphas:
        args.plot_alpha = True
        args.plot_macknhall = True

    return args

def main() -> None:
    args = parse_args()
    experiment_args = RWArgs(
        **{k: v for k, v in args.__dict__.items() if k in set(RWArgs.__match_args__) and v is not None}
    )

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
        local_strengths = experiment.run_all_phases(experiment_args)
        groups_strengths = [a | b for a, b in zip(groups_strengths, local_strengths)]
        phases[name] = experiment.phases

    assert(groups_strengths is not None)

    if args.savefig is None:
        figures = generate_figures(
            groups_strengths,
            phases = phases,
            plot_phase = args.plot_phase,
            plot_alpha = args.plot_alpha,
            plot_macknhall = args.plot_macknhall,
            plot_stimuli = args.plot_stimuli,
            dpi = args.dpi,
        )
        for fig in figures:
            fig.show()
        input('Press any key to continue...')
    else:
        save_plots(
            groups_strengths,
            phases = phases,
            filename = args.savefig,
            plot_phase = args.plot_phase,
            plot_alpha = args.plot_alpha,
            plot_macknhall = args.plot_macknhall,
            show_title = args.show_title,
            plot_stimuli = args.plot_stimuli,
            singular_legend = args.singular_legend,
            dpi = args.dpi,
        )

if __name__ == '__main__':
    with ipdb.launch_ipdb_on_exception():
        main()
