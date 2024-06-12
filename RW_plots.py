import re
import seaborn
from matplotlib import pyplot
from RW_strengths import History
from matplotlib.ticker import MaxNLocator

def titleify(filename, phases, phase_num) -> str:
    titles = []

    if filename is not None:
        titles.append(re.sub(r'\..+', '', re.sub(r'[-_]', ' ', filename)).title())

    q = max(len(v) for v in phases.values())
    title_length = max(len(k) for k in phases.keys())
    val_lengths = [max(len(v[x].phase_str) for v in phases.values()) for x in range(q)]
    for k, v in phases.items():
        group_str = [k.rjust(title_length)]
        for e, (g, v) in enumerate(zip(v, val_lengths), start = 1):
            phase_str = g.phase_str.rjust(v, '-')
            if e == phase_num:
                phase_str = fr'$\mathbf{{{phase_str}}}$'

            group_str.append(phase_str)

        titles.append('|'.join(group_str))

    return '\n'.join(titles)

def plot_graphs(data: list[dict[str, History]], *, phases = None, filename = None, plot_phase = None, plot_alpha = False, plot_macknhall = False, experiment_file = None):
    seaborn.set()

    if plot_phase is not None:
        data = [data[plot_phase - 1]]

    if filename is None:
        pyplot.ion()
    else:
        filename = filename.removesuffix('.png')

    for phase_num, experiments in enumerate(data, start = 1):
        if not plot_alpha and not plot_macknhall:
            fig, axes = pyplot.subplots(1, 1, figsize = (8, 6))
            axes = [axes]
        else:
            fig, axes = pyplot.subplots(1, 2, figsize = (16, 6))

        colors = dict(zip(experiments.keys(), seaborn.color_palette('husl', len(experiments))))
        for key, hist in experiments.items():
            axes[0].plot(hist.assoc, label=key, marker='D', color = colors[key], markersize=4, alpha=.5)

            if len(axes) > 1:
                if plot_alpha:
                    axes[1].plot(hist.alpha, label=key, color = colors[key], marker='D', markersize=8, alpha=.5)
                else:
                    axes[1].plot([], label=key, color = colors[key], marker='D', markersize=8, alpha=.5)

                if plot_macknhall:
                    axes[1].plot(hist.alpha_mack, color = colors[key], marker='$M$', markersize=8, alpha=.5)
                    axes[1].plot(hist.alpha_hall, color = colors[key], marker='$H$', markersize=8, alpha=.5)

        axes[0].set_xlabel('Trial Number')
        axes[0].set_ylabel('Associative Strength')
        axes[0].xaxis.set_major_locator(MaxNLocator(integer = True))
        axes[0].legend(fontsize = 'small')

        if plot_alpha or plot_macknhall:
            axes[0].set_title(f'Associative Strengths')
            axes[1].set_xlabel('Trial Number')
            axes[1].set_ylabel('Alpha')
            axes[1].set_title(f'Alphas')
            axes[1].xaxis.set_major_locator(MaxNLocator(integer = True))
            axes[1].yaxis.tick_right()
            axes[1].yaxis.set_label_position('right')
            axes[1].legend(fontsize = 'small')

        fig.suptitle(titleify(experiment_file, phases, phase_num), fontdict = {'family': 'monospace'}, fontsize = 12)
        fig.tight_layout()

        if len(axes) > 1:
            fig.subplots_adjust(top = .85)

        if filename is not None:
            pyplot.savefig(f'{filename}_{phase_num}.png', dpi = 300, bbox_inches = 'tight')
        else:
            pyplot.show()

    if filename is None:
        input('Press any key to continue...')
