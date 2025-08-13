from __future__ import annotations

import argparse
import random
import re
import sys
from Experiment import Experiment, Phase, RWArgs
from Environment import Environment, StimulusHistory
from Plots import generate_figures, save_plots
from AdaptiveType import AdaptiveType

# Given a list of arguments, matches the ones corresponding to a particular name
# combined with a CS and returns them as a dictionary, along with the remaining
# arguments.
def match_args(name: str, args: list[str]) -> tuple[dict[str, float], list[str]]:
    values = dict()
    rest = list()

    for arg in args:
        match = re.fullmatch(rf'--{name}[-_]([A-Z]|\([A-Z]+\))\s*=?\s*([0-9]*\.?[0-9]*)', arg)
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
  --alpha-[A-Z] α\tAssociative strength of CS A..Z.
  --alpha_mack-[A-Z] α\n\t\t\tAssociative strength (Mackintosh) of CS A..Z.
  --alpha_hall-[A-Z] α\n\t\t\tAssociative strength (Hall) of CS A..Z.
  --saliences-[A-Z] S\n\t\t\tSalience of CS A..Z.
  --habituations-[A-Z] h\n\t\t\tHabituation of CS A..Z.
''',
    )

    output = parser.add_argument_group('Output parameters')
    output.add_argument('--savefig', metavar = 'filename', type = str, help = 'Instead of showing figures, one image per phase will be saved with the name "filename_1.png" ... "filename_n.png".')
    output.add_argument('--savedata', metavar = 'filename', type = str, help = 'Instead of showing the plot, save the data to a file.')
    output.add_argument('--printdata', action = 'store_true', help = 'Instead of showing the plot, print the resulting data to stdout.')
    output.add_argument('--singular-legend', action = 'store_true', help = 'Hide legend in output, and generate a separate image with just the legend. If run with --savefig, save it under "filename_legend.png".')
    output.add_argument('--show-title', action = 'store_true', help = 'Show title and phases to saved output.')
    output.add_argument('--dpi', type = int, default = 200, help = 'Dots per inch.')
    output.add_argument('--output-width', type = int, default = 11, help = 'Width of the output')

    plot = parser.add_argument_group('Plotting parameters')
    plot.add_argument('--plot-phase', type = int, metavar = 'phase_num', help = 'Plot a single phase')
    plot.add_argument("--plot-experiments", metavar = 'group', nargs = '*', help = 'List of experiments to plot.')
    plot.add_argument("--plot-stimuli", nargs = '*', metavar = 'conditioned_stimulus', help = 'List of stimuli, compound and simple, to plot.')
    plot.add_argument('--plot-alpha', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot the total alpha.')
    plot.add_argument('--plot-macknhall', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot the alpha Mack and alpha Hall.')
    plot.add_argument('--plot-alphas', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot all the alphas, including total alpha, alpha Mack, and alpha Hall.')
    plot.add_argument('--part-stimuli', type = bool, action = argparse.BooleanOptionalAction, help = 'Whether to plot part stimuli with US in addition to the regular plot.')

    experiment = parser.add_argument_group('Experiment Parameters')
    experiment.add_argument("--adaptive-type", choices = AdaptiveType.types().keys(), default = 'Rescorla Wagner', help = 'Type of adaptive attention mode to use')
    experiment.add_argument('--alpha', metavar = 'α', type = float, default = .1, help = 'Alpha for all other stimuli')
    experiment.add_argument('--alpha-mack', metavar = 'αᴹ', type = float, default = .1, help = 'Alpha_mack for all other stimuli')
    experiment.add_argument('--alpha-hall', metavar = 'αᴴ', type = float, default = .1, help = 'Alpha_hall for all other stimuli')
    experiment.add_argument("--beta", metavar = 'β⁺', type = float, default = .3, help="Associativity of the US +.")
    experiment.add_argument("--beta-neg", metavar = 'β⁻', type = float, default = .2, help="Associativity of the absence of US +. Equal to beta by default.")
    experiment.add_argument("--lamda", metavar = 'λ', type = float, default = 1, help="Asymptote of learning.")
    experiment.add_argument("--gamma", metavar = 'γ', type = float, default = .15, help = "Weighting how much you rely on past experinces on DualV adaptive type.")
    experiment.add_argument("--thetaE", metavar = 'θᴱ', type = float, default = .3, help = "Theta for excitatory phenomena in LePelley blocking")
    experiment.add_argument("--thetaI", metavar = 'θᴵ', type = float, default = .1, help = "Theta for inhibitory phenomena in LePelley blocking")
    experiment.add_argument("--salience", metavar = 'S', type = float, default = .5, help = 'Salience for all parameters without an individually defined salience. This is used in the Pearce & Hall model.')
    experiment.add_argument("--habituation", metavar = 'h', type = float, default = .99, help = 'Habituation delay for all parameters in the hybrid model.')
    experiment.add_argument("--xi-hall", metavar = 'ξ', type = float, default = 0.2, help = 'Xi parameter for Hall alpha calculation')
    experiment.add_argument("--num-trials", metavar = '№', type = int, default = 100, help = 'Amount of trials done in randomised phases')
    experiment.add_argument("--configural-cues", type = bool, default = False, action = argparse.BooleanOptionalAction, help = 'Whether to use configural cues')
    experiment.add_argument("--rho", metavar = 'ρ', type = float, default = .2)
    experiment.add_argument("--nu", metavar = 'ν', type = float, default = .25)
    experiment.add_argument("--kay", metavar = 'κ', type = float, default = 2)


    parser.add_argument(
        "experiment_file",
        nargs = '?',
        type = argparse.FileType('r'),
        default = sys.stdin,
        help = "Path to the experiment file."
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
        if experiment.startswith('@'):
            for prop in experiment.strip('@').strip().split(';'):
                name, value = prop.split('=')
                experiment_args.set_value(name, value)
            continue

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

    if args.savefig is None and args.savedata is None and not args.printdata:
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
        if args.savefig is not None:
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
                plot_width = args.output_width,
            )

        if args.savedata is not None:
            with open(args.savedata, 'w') as file:
                StimulusHistory.exportData(
                    groups_strengths,
                    file = file,
                    should_plot_macknhall = args.plot_macknhall,
                )

        if args.printdata:
            StimulusHistory.exportData(
                groups_strengths,
                file = sys.stdout,
                should_plot_macknhall = args.plot_macknhall,
            )

if __name__ == '__main__':
    main()
