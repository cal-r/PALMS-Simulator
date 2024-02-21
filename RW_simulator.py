import argparse
import pprint
import re
import sys
from matplotlib import pyplot
import seaborn
import random
from collections import defaultdict
from matplotlib.ticker import StrMethodFormatter, MaxNLocator
from RW_group import Group
from typing import List

def parse_args():
    parser = argparse.ArgumentParser(
        description="Behold! My Rescorla-Wagnerinator!",
        epilog = '--alpha_[A-Z] ALPHA\tAssociative strength of CS A..Z. By default 0.2',
    )

    parser.add_argument("--beta", type = float, default = 1, help="Associativity of the US +.")
    parser.add_argument("--beta-neg", type = float, default = None, help="Associativity of the absence of US +. Equal to beta by default.")
    parser.add_argument("--lamda", type = float, default = 1, help="Asymptote of learning.")
    parser.add_argument("--lamda-neg", type = float, default = None, help="Asymptote of the absence of US +. 0 by default.")

    parser.add_argument("--use-configurals", type = bool, action = argparse.BooleanOptionalAction, help = 'Use compound stimuli with configural cues')

    # parser.add_argument("--use-adaptive", type = bool, action = argparse.BooleanOptionalAction, help = 'Use adaptive attention mode')
    parser.add_argument("--adaptive-type", choices = ['linear', 'exponential'], help = 'Type of adaptive attention mode to use')
    parser.add_argument("--window-size", type = int, default = None, help = 'Size of sliding window for adaptive learning')

    parser.add_argument("--plot-experiments", nargs = '*', help = 'List of experiments to plot. By default plot everything')
    parser.add_argument("--plot-stimuli", nargs = '*', help = 'List of stimuli, compound and simple, to plot. By default plot everything')


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
        match = re.fullmatch('--alpha_([A-Z])\s*=?\s*([0-9]*\.?[0-9]*)', arg)
        if not match:
            parser.error(f'Option not understood: {arg}')

        args.alphas[match.group(1)] = float(match.group(2))

    if args.beta_neg is None:
        args.beta_neg = args.beta

    if args.lamda_neg is None:
        args.lamda_neg = 0

    if args.use_configurals is None:
        args.use_configurals = False

    args.use_adaptive = args.adaptive_type is not None

    return args

def parse_parts(phase : str) -> List[str]:
    rand = False
    parts_str = phase.strip().split('/')
    if parts_str[0] == 'rand':
        rand = True
        parts_str = parts_str[1:]

    parts = []
    for part in parts_str:
        num, cs, sign = re.fullmatch('([0-9]*)([A-Z]+)([+-]?)', part).groups()

        if num is None:
            num = '1'

        if sign == '':
            sign = '+'

        parts += int(num) * [(cs, sign)]

    if rand:
        random.shuffle(parts)

    return parts

def run_group_experiments(g, experiment):
    results = []

    for trial, phase in enumerate(experiment):
        V, A = g.runPhase(phase)
        results.append((V, A))

    return results

'''
def plot_graphs(data : list[dict[str, list[int]]]):
    seaborn.set()
    pyplot.ion()

    for e, lines in enumerate(data, start = 1):
        pyplot.figure(figsize = (8, 3))

        for val, points in lines.items():
            pyplot.plot(points, label = val, marker = 'D', markersize = 4, alpha = .5)

        pyplot.xlabel('Trial Number')
        pyplot.ylabel('Associative Strength')

        pyplot.gca().set_xticks(range(max(len(x) for x in lines.values())))

        pyplot.gca().xaxis.set_major_locator(MaxNLocator(integer = True, nbins = 'auto'))
        # pyplot.gca().xaxis.set_major_formatter(StrMethodFormatter('{x:.0f}'))
        pyplot.title(f'Phase {e}') 

        pyplot.subplots_adjust(bottom=0.40)
        pyplot.legend(loc='upper center', bbox_to_anchor=(.5, -.37), ncol = 3)
        # pyplot.tight_layout()
        pyplot.show()

    input('Press any key to continue...')
'''
def plot_graphs(data: list[dict[str, list[int]]], alpha_data: list[dict[str, list[float]]]):
    seaborn.set()
    pyplot.ion()

    for e, (lines, alpha_lines) in enumerate(zip(data, alpha_data), start=1):
        pyplot.figure(figsize=(16, 6))

        # Plot for associative strengths
        ax1 = pyplot.subplot(1, 2, 1)
        for val, points in lines.items():
            ax1.plot(points, label=val, marker='D', markersize=4, alpha=.5)
        ax1.set_xlabel('Trial Number')
        ax1.set_ylabel('Associative Strength')
        ax1.set_title(f'Phase {e} Associative Strengths')
        ax1.legend()

        # Plot for alpha values
        ax2 = pyplot.subplot(1, 2, 2)
        for val, points in alpha_lines.items():
            ax2.plot(points, label=f'Alpha - {val}', linestyle='--', marker='o', markersize=4, alpha=.5)
        ax2.set_xlabel('Trial Number')
        ax2.set_ylabel('Alpha Value')
        ax2.set_title(f'Phase {e} Alpha Values')
        ax2.legend()

        pyplot.tight_layout()
        pyplot.show()

    input('Press any key to continue...')


def main():
    args = parse_args()

    groups_strengths = []
    alpha_values = []

    for e, experiment in enumerate(args.experiment_file.readlines()):
        name, *phases = experiment.split('|')
        name = name.strip()
        phases = [parse_parts(phase) for phase in phases]

        cs = set(''.join(y[0] for x in phases for y in x))
        g = Group(name, args.alphas, args.beta_neg, args.beta, args.lamda_neg, args.lamda, cs, args.use_configurals, args.adaptive_type, args.window_size)

        for e, (strengths, alphas) in enumerate(run_group_experiments(g, phases)):
            if len(groups_strengths) <= e:
                groups_strengths.append({})

            groups_strengths[e] |= {
                f'{name} - {k}': v
                for k, v in strengths.items()
                if (args.plot_experiments is None or name in args.plot_experiments) and
                   (args.plot_stimuli is None or k in args.plot_stimuli)
            }

            if len(alpha_values) <= e:
                alpha_values.append({})

            alpha_values[e] |= {
                f'{name} - {k}': v
                for k, v in alphas.items()
                if (args.plot_experiments is None or name in args.plot_experiments) and
                   (args.plot_stimuli is None or k in args.plot_stimuli)
            }

    #plot_graphs(groups_strengths)
    plot_graphs(groups_strengths, alpha_values)

if __name__ == '__main__':
    main()
