from __future__ import annotations

import re
import seaborn
import matplotlib
matplotlib.use('QtAgg')

from matplotlib import pyplot
from Environment import StimulusHistory
from matplotlib.ticker import MaxNLocator, IndexLocator, LinearLocator
from matplotlib.ticker import FuncFormatter
from matplotlib.axes import Axes
from itertools import chain
from typing import Any, TypeAlias

from Experiment import Phase

Color: TypeAlias = tuple[float, float, float]

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

    ret = '\n'.join(titles)
    if len(ret) <= 100:
        return ret
    
    return ''

def get_css(data: list[dict[str, StimulusHistory]]) -> tuple[list[str], dict[str, Color], dict[str, Color], dict[str, str]]:
    css = sorted(set(chain.from_iterable([x.keys() for x in data])), key = lambda x: (len(x), x))

    colors = dict(zip(css, seaborn.husl_palette(len(css), s=.9, l=.5)))
    colors_alt = dict(zip(css, seaborn.hls_palette(len(css), l=.7)))

    # markers = ['*', 'X', 'D', 's', 'o', 'd', 'p', 'h', '^', 'v', '<', '>']
    markers = ['o', 's', 'D', '^', 'v', '<', '>', 'p', '*', 'h', 'X', 'd']
    marker_dict = dict(zip(css, [markers[i % len(markers)] for i in range(len(css))]))

    colors['Real-world Group - X'], colors['Real-world Group - Y'] = seaborn.husl_palette(2)
    return css, colors, colors_alt, marker_dict

def generate_figures(
        data: list[dict[str, StimulusHistory]],
        *,
        phases: None | dict[str, list[Phase]] = None,
        title: None | str = None,
        plot_phase: None | int = None,
        plot_V: bool = True,
        plot_alpha: bool = False,
        plot_macknhall: bool = False,
        plot_stimuli: None | list[str] = None,
        dpi: None | float = None,
        ticker_threshold: bool = False,
        singular_legend: bool = False,
    ) -> list[pyplot.Figure]:
    seaborn.set()

    if plot_phase is not None:
        data = [data[plot_phase - 1]]

    experiment_css, colors, colors_alt, markers = get_css(data)

    figures = []
    for phase_num, experiments in enumerate(data, start = 1):
        multiple = False
        if not plot_V or not plot_alpha and not plot_macknhall:
            fig, axes_ = pyplot.subplots(1, 1, figsize = (8, 6), dpi = dpi)
            axes = [axes_]
        else:
            fig, axes = pyplot.subplots(1, 2, figsize = (16, 6), dpi = dpi)
            multiple = True

        def sort_key(key):
            group, cs = key.split(' - ')
            return group, -len(cs), cs

        sorted_exp = sorted(experiments, key = sort_key)
        for num, key in enumerate(sorted_exp):
            hist = experiments[key]
            stimulus = key.split(' ')[-1]
            if plot_stimuli is not None and stimulus not in plot_stimuli:
                continue

            ratio = 0.
            if len(experiments) > 1:
                ratio = num / (len(experiments.items()) - 1)

            plot_options = dict(
                marker = markers[key],
                color = colors[key],
                markersize = 4,
                alpha = 1 - .5 * ratio,
                picker = ticker_threshold,
            )

            ax = axes[0]
            if plot_V:
                line = ax.plot(hist.assoc, label = key, **plot_options) # type: ignore
                if multiple:
                    ax = axes[1]

            cs = key.rsplit(' ', 1)[1]
            if plot_alpha and not plot_macknhall:
                ax.plot(hist.alpha, label='α: '+str(key), **plot_options) # type: ignore

            if plot_macknhall:
                ax.plot(hist.alpha_mack, label='Mack: ' + str(key), color = colors[key],     marker='$M$', markersize=6, alpha=1, picker = ticker_threshold)
                ax.plot(hist.alpha_hall, label='Hall: ' + str(key), color = colors_alt[key], marker='$H$', markersize=6, alpha=1, picker = ticker_threshold)

        # Matplotlib makes it hard to start a plot with xticks = [1, t].
        # Instead of fixing the ticks ourselves, we plot in [0, t - 1] and format
        # the ticks to appear as the next number.
        axes[0].set_xlabel('Trial Number', fontsize = 'small', labelpad = 3)
        # axes[0].set_ylim(lowest, highest)
        axes[0].ticklabel_format(useOffset = False, style = 'plain', axis = 'y')
        axes[0].tick_params(axis = 'both', labelsize = 'x-small', pad = 1)
        axes[0].xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x + 1:.0f}'))
        axes[0].xaxis.set_major_locator(MaxNLocator(integer = True, min_n_ticks = 1))
        axes[0].yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.1f}'))

        if plot_V:
            axes[0].set_ylabel('Associative Strength', fontsize = 'small', labelpad = 3)
        else:
            axes[0].set_ylabel('Alpha', fontsize = 'small', labelpad = 3)

        if multiple:
            axes[0].set_title(f'Associative Strengths')

            axes[1].set_title(f'Learning Rate')
            axes[1].set_xlabel('Trial Number', fontsize = 'small', labelpad = 3)
            axes[1].set_ylabel('Alpha', fontsize = 'small', labelpad = 3)
            # axes[1].set_ylim(lowest, highest)
            axes[1].tick_params(axis = 'both', labelsize = 'x-small', pad = 1)
            axes[1].tick_params(axis = 'y', which = 'both', right = True, length = 0)
            axes[1].xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x + 1:.0f}'))
            axes[1].xaxis.set_major_locator(MaxNLocator(integer = True))
            axes[1].xaxis.set_major_locator(MaxNLocator(integer = True, min_n_ticks = 1))
            axes[1].yaxis.set_label_position('right')
            axes[1].yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.1f}'))
            axes[1].yaxis.tick_right()

        if not singular_legend and len(experiments) < 50:
            properties: dict[str, Any]
            if len(experiments) >= 6:
                properties = dict(fontsize = 7, ncol = 2)
            else:
                properties = dict(fontsize = 'x-small')

            for ax in axes:
                legend = ax.legend(**properties)
                legend.set_draggable(True)
                for legend_line in legend.get_lines():
                    legend_line.set_alpha(1)
                    legend_line.set_picker(1)

        if phases is not None:
            title = titleify(title, phases, phase_num)
            if title:
                fig.suptitle(title, fontdict = {'family': 'monospace'}, fontsize = 12)

            if len(axes) > 1:
                fig.subplots_adjust(top = .85)

        fig.tight_layout()
        figures.append(fig)

    return figures

def generate_legend(data, plot_stimuli, dpi):
    css, colors, _, markers = get_css(data)
    fig = pyplot.figure(dpi = dpi)
    pyplot.axis('off')
    for exp in css:
        if plot_stimuli is not None and exp.split(' ')[-1] not in plot_stimuli:
            continue

        pyplot.plot([], [], figure = fig, color = colors[exp], marker = markers[exp], label = exp)

    fig.legend(ncols = len(exp), frameon = True, handlelength = 1, loc = 'center')
    fig.canvas.draw()
    return fig

def save_plots(
    data: list[dict[str, StimulusHistory]],
    *,
    phases: None | dict[str, list[Phase]] = None,
    filename: None | str = None,
    plot_phase: None | int = None,
    plot_stimuli: None | list[str] = None,
    plot_V: bool = True,
    plot_alpha: bool = False,
    plot_macknhall: bool = False,
    dpi: int = 200,
    show_title: bool = False,
    singular_legend: bool = False,
    plot_width: int = 11,
    plot_height: int = 2,
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
        legend_fig = generate_legend(data, plot_stimuli, dpi)
        legend_fig.set_size_inches(plot_width, .1)
        legend_fig.savefig(f'{filename}_legend.png', dpi = dpi or 150, bbox_inches = 'tight', pad_inches = 0)

    for phase_num, fig in enumerate(figures, start = plot_phase or 1):
        dep = 1.3
        if plot_phase is None and phase_num > 1:
            fig.axes[0].set_title('')
            fig.axes[0].set_ylabel('')
            fig.axes[0].set_yticklabels([])

        fig.set_size_inches(plot_width / dep, plot_height / dep)
        # widths = {1: 5, 2: 2, 3: 5}
        # fig.set_size_inches(widths[phase_num] / dep, 2 / dep)
        fig.savefig(f'{filename}_{phase_num}.png', dpi = dpi or 150, bbox_inches = 'tight')
