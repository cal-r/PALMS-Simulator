from __future__ import annotations

import re
import seaborn
import matplotlib
import numpy as np
matplotlib.use('QtAgg')

from matplotlib import pyplot
from Environment import StimulusHistory
from matplotlib.ticker import MaxNLocator, IndexLocator, LinearLocator
from matplotlib.ticker import FuncFormatter
from itertools import chain

from Experiment import Phase

def titleify(filename: None | str, phases: dict[str, list[Phase]], phase_num: int, suffix: None | str) -> str:
    titles = []

    if filename is not None:
        filename = re.sub(r'.*\/|\..+', '', re.sub(r'[-_]', ' ', filename))
        filename = filename.title().replace('Lepelley', 'LePelley').replace('Dualv', 'DualV')
        if suffix is not None:
            filename = f'{filename} ({suffix})'

        titles.append(filename)

    q = max(len(v) for v in phases.values())
    title_length = max(len(k) for k in phases.keys())
    val_lengths = [max(len(v[x].phase_str) for v in phases.values()) for x in range(q)]
    for k, v in phases.items():
        group_str = [k.rjust(title_length)]
        for e, (g, ln) in enumerate(zip(v, val_lengths), start = 1):
            phase_str = g.phase_str
            if e == phase_num:
                phase_str = fr'$\mathbf{{{phase_str}}}$'

            phase_str = (ln - len(g.phase_str)) * ' ' + phase_str

            group_str.append(phase_str)

        titles.append('|'.join(group_str))

    return '\n'.join(titles)

def generate_figures(
        data: list[dict[str, StimulusHistory]],
        *,
        phases: None | dict[str, list[Phase]] = None,
        filename: None | str = None,
        plot_phase: None | int = None,
        plot_alpha: bool = False,
        plot_macknhall: bool = False,
        title_suffix: None | str = None,
        dpi: None | float = None,
        ticker_threshold: int = 10,
    ) -> list[pyplot.Figure]:
    seaborn.set()

    if plot_phase is not None:
        data = [data[plot_phase - 1]]

    experiment_css = sorted(set(chain.from_iterable([x.keys() for x in data])))
    colors = dict(zip(experiment_css, seaborn.husl_palette(len(experiment_css))))
    colors_alt = dict(zip(experiment_css, seaborn.hls_palette(len(experiment_css))))

    figures = []
    for phase_num, experiments in enumerate(data, start = 1):
        multiple = False
        if not plot_alpha and not plot_macknhall:
            fig, axes_ = pyplot.subplots(1, 1, figsize = (8, 4), dpi = dpi)
            axes = [axes_]
        else:
            fig, axes = pyplot.subplots(1, 2, figsize = (16, 6), dpi = dpi)
            multiple = True

        for key, hist in experiments.items():
            # This is a predictive model. Do not include the last stimulus in the plot.
            hist = hist[:-1]

            line = axes[0].plot(hist.assoc, label = key, marker = 'D', color = colors[key], markersize = 4, alpha = .5, picker = ticker_threshold)

            cs = key.rsplit(' ', 1)[1]
            if multiple:
                if plot_alpha and not plot_macknhall:
                    axes[1].plot(hist.alpha, label='α: '+str(key), color = colors[key], marker='D', markersize=4, alpha=.5, picker = ticker_threshold)

                if plot_macknhall:
                    axes[1].plot(hist.alpha_mack, label='Mack: ' + str(key), color = colors[key], marker='$M$', markersize=4, alpha=.5, picker = ticker_threshold)
                    axes[1].plot(hist.alpha_hall, label='Hall: ' + str(key), color = colors_alt[key], marker='$H$', markersize=4, alpha=.5, picker = ticker_threshold)

        axes[0].set_xlabel('Trial Number', fontsize = 'small', labelpad = 3)
        axes[0].set_ylabel('Associative Strength', fontsize = 'small', labelpad = 3)

        axes[0].tick_params(axis = 'both', labelsize = 'x-small', pad = 1)
        axes[0].ticklabel_format(useOffset = False, style = 'plain', axis = 'y')

        # UGLY HACK WARNING.
        # Matplotlib makes it hard to start a plot with xticks = [1, t].
        # Instead of fixing the ticks ourselves, we plot in [0, t - 1] and format
        # the ticks to appear as the next number.
        axes[0].xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x + 1:.0f}'))
        axes[0].xaxis.set_major_locator(MaxNLocator(integer = True, min_n_ticks = 1))

        if len(experiments) >= 6:
            axes[0].legend(fontsize = 8, ncol = 2).set_draggable(True)
        else:
            axes[0].legend(fontsize = 'x-small').set_draggable(True)

        if multiple:
            axes[0].set_title(f'Associative Strengths')
            axes[1].set_xlabel('Trial Number', fontsize = 'small', labelpad = 3)
            axes[1].set_ylabel('Alpha', fontsize = 'small', labelpad = 3)
            axes[1].set_title(f'Alphas')
            axes[1].xaxis.set_major_locator(MaxNLocator(integer = True))
            axes[1].yaxis.tick_right()
            axes[1].tick_params(axis = 'both', labelsize = 'x-small', pad = 1)
            axes[1].tick_params(axis = 'y', which = 'both', right = True, length = 0)
            axes[1].yaxis.set_label_position('right')
            axes[1].xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x + 1:.0f}'))
            axes[1].xaxis.set_major_locator(MaxNLocator(integer = True, min_n_ticks = 1))
            if len(experiments) >= 6:
                axes[1].legend(fontsize = 8, ncol = 2).set_draggable(True)
            else:
                axes[1].legend(fontsize = 'x-small').set_draggable(True)

        legend_lines = chain.from_iterable([ax.get_legend().get_lines() for ax in axes])
        for legend_line in legend_lines:
            legend_line.set_picker(ticker_threshold)

        if phases is not None:
            fig.suptitle(titleify(filename, phases, phase_num, title_suffix), fontdict = {'family': 'monospace'}, fontsize = 12)

            if len(axes) > 1:
                fig.subplots_adjust(top = .85)

        fig.tight_layout()
        figures.append(fig)

    return figures

def show_plots(data: list[dict[str, StimulusHistory]], *, phases: None | dict[str, list[Phase]] = None, plot_phase = None, plot_alpha = False, plot_macknhall = False, dpi = None):
    figures = generate_figures(
        data = data,
        phases = phases,
        plot_phase = plot_phase,
        plot_alpha = plot_alpha,
        plot_macknhall = plot_macknhall,
        dpi = dpi,
        ticker_threshold = True,
    )
    return figures

def save_plots(data: list[dict[str, StimulusHistory]], *, phases: None | dict[str, list[Phase]] = None, filename: None | str = None, plot_phase = None, plot_alpha = False, plot_macknhall = False, title_suffix = None, dpi = None):
    if filename is not None:
        filename = filename.removesuffix('.png')

    figures = generate_figures(
        data = data,
        phases = phases,
        plot_phase = plot_phase,
        plot_alpha = plot_alpha,
        plot_macknhall = plot_macknhall,
        filename = filename,
        title_suffix = title_suffix,
        dpi = dpi,
    )

    for phase_num, fig in enumerate(figures, start = 1):
        fig.savefig(f'{filename}_{phase_num}.png', dpi = dpi or 150, bbox_inches = 'tight')
