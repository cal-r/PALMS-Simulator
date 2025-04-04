from __future__ import annotations

import re
import seaborn
import matplotlib
import numpy
matplotlib.use('QtAgg')

from matplotlib import pyplot
from Environment import StimulusHistory
from matplotlib.ticker import MaxNLocator, IndexLocator, LinearLocator
from matplotlib.ticker import FuncFormatter
from matplotlib.axes import Axes
from itertools import chain
from typing import Any

from Experiment import Phase

def titleify(title: None | str, phases: dict[str, list[Phase]], phase_num: int) -> str:
    titles = []

    if title is not None:
        title = re.sub(r'.*\/|\..+', '', re.sub(r'[-_]', ' ', title))
        title = title.title().replace('Lepelley', 'LePelley').replace('Dualv', 'DualV')
        titles.append(title)

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
        title: None | str = None,
        plot_phase: None | int = None,
        plot_alpha: bool = False,
        plot_macknhall: bool = False,
        plot_stimuli: None | list[str] = None,
        dpi: None | float = None,
        ticker_threshold: int = 10,
        singular_legend: bool = False,
    ) -> list[pyplot.Figure]:
    seaborn.set()

    if plot_phase is not None:
        data = [data[plot_phase - 1]]

    experiment_css = sorted(set(chain.from_iterable([x.keys() for x in data])))
    colors = dict(zip(experiment_css, seaborn.husl_palette(len(experiment_css), s=.9, l=.5)))
    colors_alt = dict(zip(experiment_css, seaborn.hls_palette(len(experiment_css), l=.7)))

    # markers = ['*', 'X', 'D', 's', 'o', 'd', 'p', 'h', '^', 'v', '<', '>']
    markers = ['o', 's', 'D', '^', 'v', '<', '>', 'p', '*', 'h', 'X', 'd']
    marker_dict = dict(zip(experiment_css, [markers[i % len(markers)] for i in range(len(experiment_css))]))

    eps = 1e-1
    lowest  = min(0, min(min(hist.assoc) for experiments in data for hist in experiments.values())) - eps
    highest = max(1, max(max(hist.assoc) for experiments in data for hist in experiments.values())) + eps

    figures = []
    for phase_num, experiments in enumerate(data, start = 1):
        multiple = False
        if not plot_alpha and not plot_macknhall:
            fig, axes_ = pyplot.subplots(1, 1, figsize = (8, 6), dpi = dpi)
            axes = [axes_]
        else:
            fig, axes = pyplot.subplots(1, 2, figsize = (16, 6), dpi = dpi)
            multiple = True

        for num, (key, hist) in enumerate(experiments.items()):
            # This is a predictive model. Do not include the last stimulus in the plot.
            hist = hist[:-1]

            stimulus = key.split(' ')[-1]
            if plot_stimuli is not None and stimulus not in plot_stimuli:
                continue

            ratio = num / (len(experiments.items()) - 1)
            line = axes[0].plot(
                hist.assoc,
                label = key,
                marker = marker_dict[key],
                color = colors[key],
                markersize = 4,
                alpha = 1 - .5 * ratio,
                picker = ticker_threshold
            )

            cs = key.rsplit(' ', 1)[1]
            if multiple:
                if plot_alpha and not plot_macknhall:
                    axes[1].plot(hist.alpha, label='α: '+str(key), color = colors[key], marker='D', markersize=4, alpha=1, picker = ticker_threshold)

                if plot_macknhall:
                    axes[1].plot(hist.alpha_mack, label='Mack: ' + str(key), color = colors[key], marker='$M$', markersize=6, alpha=1, picker = ticker_threshold)
                    axes[1].plot(hist.alpha_hall, label='Hall: ' + str(key), color = colors_alt[key], marker='$H$', markersize=6, alpha=1, picker = ticker_threshold)

        axes[0].set_xlabel('Trial Number', fontsize = 'small', labelpad = 3)
        axes[0].set_ylabel('Associative Strength', fontsize = 'small', labelpad = 3)

        axes[0].tick_params(axis = 'both', labelsize = 'x-small', pad = 1)
        axes[0].ticklabel_format(useOffset = False, style = 'plain', axis = 'y')

        # Matplotlib makes it hard to start a plot with xticks = [1, t].
        # Instead of fixing the ticks ourselves, we plot in [0, t - 1] and format
        # the ticks to appear as the next number.
        axes[0].xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x + 1:.0f}'))
        axes[0].xaxis.set_major_locator(MaxNLocator(integer = True, min_n_ticks = 1))

        axes[0].yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.1f}'))

        axes[0].set_ylim(lowest, highest)

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
            axes[1].set_ylim(lowest, highest)

        if not singular_legend:
            properties: dict[str, Any]
            if len(experiments) >= 6:
                properties = dict(fontsize = 7, ncol = 2)
            else:
                properties = dict(fontsize = 'x-small')

            for ax in axes:
                legend = ax.legend(**properties)
                for legend_line in legend.get_lines():
                    legend_line.set_alpha(1)
                    legend_line.set_picker(10)

        if phases is not None:
            fig.suptitle(titleify(title, phases, phase_num), fontdict = {'family': 'monospace'}, fontsize = 12)

            if len(axes) > 1:
                fig.subplots_adjust(top = .85)

        fig.tight_layout()
        figures.append(fig)

    if singular_legend:
        fig = pyplot.figure(dpi = dpi)
        pyplot.axis('off')
        for exp in experiment_css:
            pyplot.plot([], [], figure = fig, color = colors[exp], marker = marker_dict[exp], label = exp)

        legend = fig.legend(
            ncols = len(exp),
            frameon = True,
            handlelength = 1,
            loc = 'center',
        )
        fig.canvas.draw()

        figures.append(fig)

    return figures

def save_plots(
    data: list[dict[str, StimulusHistory]],
    *,
    phases: None | dict[str, list[Phase]] = None,
    filename: None | str = None,
    plot_phase: None | int = None,
    plot_stimuli: None | list[str] = None,
    plot_alpha: bool = False,
    plot_macknhall: bool = False,
    dpi: int = 200,
    show_title: bool = False,
    singular_legend: bool = False,
    plot_width: int = 11,
):
    if filename is not None:
        filename = filename.removesuffix('.png')

    title = None
    if show_title:
        title = filename
    else:
        phases = None

    figures = generate_figures(
        data = data,
        phases = phases,
        plot_phase = plot_phase,
        plot_stimuli = plot_stimuli,
        plot_alpha = plot_alpha,
        plot_macknhall = plot_macknhall,
        title = title,
        dpi = dpi,
        singular_legend = singular_legend,
    )

    if singular_legend:
        legend_fig = figures[-1]
        figures = figures[:-1]
        legend_fig.set_size_inches(11, .1)
        legend_fig.savefig(f'{filename}_legend.png', dpi = dpi or 150, bbox_inches = 'tight', pad_inches = 0)

    for phase_num, fig in enumerate(figures, start = 1):
        dep = 1.3
        if phase_num < len(figures):
            fig.axes[0].set_xlabel(f'')

        fig.set_size_inches(plot_width / dep, 2 / dep)
        fig.savefig(f'{filename}_{phase_num}.png', dpi = dpi or 150, bbox_inches = 'tight')
