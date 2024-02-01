import argparse
import re
import sys
import matplotlib.pyplot as plt
import seaborn
import random
from collections import defaultdict
from matplotlib.ticker import StrMethodFormatter
from RW_group import Group

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
    parser.add_argument("--use-adaptive", type = bool, action = argparse.BooleanOptionalAction, help = 'Use adaptive attention mode')
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

    if args.use_adaptive is None:
        args.use_adaptive = False

    return args

def run_group_experiments(g, experiment):
    as_strengths = []

    for trial, phase in enumerate(experiment):
        if trial == 0 and len(phase) == 1 and re.fullmatch('([0-9]*)([A-Z]+)([+-]?)', phase[0]) is None:
            # If this is the leftmost element of the experiment and it doesn't
            # match our regex, it's likely a group name.
            g.name = phase[0]
            continue
        
        if len(phase) > 1 and phase[0].lower() == 'rand':
            value = run_random_phase(g, phase[1:])
        else:
            value = run_sequential_phase(g, phase)

        as_strengths.append(value)

    return as_strengths

def run_random_phase(g, phase):
    matches = [re.fullmatch('([0-9]*)([A-Z]+)([+-]?)', part).groups() for part in phase]
    parts = sum((int(steps) * [(1, conds, plus == '+')] for steps, conds, plus in matches), [])
    random.shuffle(parts)

    phase_value = [[] for _ in parts]
    for e, (steps, conds, plus) in enumerate(parts):
        V = g.runPhase(steps, conds, plus, ret_V = True)
        phase_value[e].append(V)

        print(V)
        for k, v in V.items():
            print(f'{g.name} group, phase [{"/".join(phase)}], Cue ({k}) ⟶  (+):')
            for e, q in enumerate(v):
                print(f'\tV_{e} = {q:g}')

    return phase_value

def run_sequential_phase(g, phase):
    phase_value = []
    for part_num, part in enumerate(phase):
        match = re.fullmatch('([0-9]*)([A-Z]+)([+-]?)', part)
        if match is None:
            raise ValueError(f'Part of phase "{match}" not understood')

        steps = int(match.group(1)) if match.group(1) else 0
        conds = match.group(2)
        plus = match.group(3) == '+'

        V = g.runPhase(steps, conds, plus, ret_V = True)
        phase_value.append(V)

        print(V)
        for k, v in V.items():
            print(f'{g.name} group, phase [{"/".join(phase)}], Cue ({k}) ⟶  (+):')
            for e, q in enumerate(v):
                print(f'\tV_{e} = {q:g}')

    return phase_value

def plot_graphs(groups_strengths, group_names, plot_stimuli = None):
    seaborn.set()
    plt.ion()
    # Iterate through phases
    min_y = 0 
    for i in range(len(groups_strengths[0])):
        plt.figure(figsize = (8, 3))

        # Iterate through groups
        for j in range(len(groups_strengths)):
            #for e in range(len(phase_group)-1):
            for stimuli in groups_strengths[j][i]:
                for k, v in stimuli.items():
                    if plot_stimuli is not None and k not in plot_stimuli:
                        continue

                    indices = list(range(len(v)))
                    min_y = min(min_y, min(v))
                    plt.plot(indices, v, label=f'{group_names[j]} {k}', marker = 'D', markersize = 4)

        plt.xlabel('Trial Number')
        plt.ylabel('Associative Strength')
        plt.ylim(min_y - .1, 1.1)
        plt.gca().xaxis.set_major_formatter(StrMethodFormatter('{x:.0f}'))
        plt.title(f'Phase {i+1}') 

        plt.subplots_adjust(bottom=0.40)
        plt.legend(loc='upper center', bbox_to_anchor=(.5, -.37), ncol = 3)
        plt.show()

    input('Press any key to continue...')

def main():
    args = parse_args()

    experiments = [[y.strip().split('/') for y in x.strip().split('|')] for x in args.experiment_file.readlines()]
    groups_strengths = []
    group_names = ['Control', 'Test']
    for e, group in enumerate(experiments):
        cs = set(re.findall('[A-Z]', ''.join(y for y in sum(group, []) if y.upper() == y)))
        g = Group(args.alphas, args.beta_neg, args.beta, args.lamda_neg, args.lamda, cs, args.use_configurals, args.use_adaptive)
        group_strength = run_group_experiments(g, group)
        groups_strengths.append(group_strength)

    plot_graphs(groups_strengths, group_names, args.plot_stimuli)
if __name__ == '__main__':
    main()
