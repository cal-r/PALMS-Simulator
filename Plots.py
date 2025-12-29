from __future__ import annotations

import colorcet
import re
import math
import logging
import colorsys
from itertools import islice, cycle, chain

from Environment import StimulusHistory
from Experiment import Phase
from itertools import chain
from typing import Any, TypeAlias

from matplotlib.textpath import TextPath
from matplotlib.markers import MarkerStyle
from matplotlib.font_manager import FontProperties

Color: TypeAlias = tuple[float, float, float]

def titleify(title: None | str, phases: dict[str, list[Phase]], phase_num: int) -> str:
    titles = []

    if title is not None:
        title = re.sub(r'.*\/|\..+', '', re.sub(r'[-_]', ' ', title))
        title = title.title().replace('Dualv', 'DualV')
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

def get_css(data: list[dict[str, StimulusHistory]]) -> tuple[list[str], dict[str, Color], dict[str, str]]:
    import seaborn
    css = sorted(set(chain.from_iterable([x.keys() for x in data])), key = lambda x: (len(x), x))

    color_list = list(islice(cycle(colorcet.glasbey), len(css)))
    colors = dict(zip(css, color_list))

    markers = ['o', 's', 'D', '^', 'v', '<', '>', 'p', '*', 'h', 'X', 'd']
    marker_dict = dict(zip(css, [markers[i % len(markers)] for i in range(len(css))]))

    colors['Real-world Group - X'], colors['Real-world Group - Y'] = seaborn.husl_palette(2)
    return css, colors, marker_dict

# Plot a complex marker with an invisible square around it for rediability.
def plot_around_marker(data, char, label, color, ax, **kwargs):
    bg = ax.get_facecolor()
    marker = f'${char}$'
    size = 6

    ax.plot(
        data,
        color = color,
        zorder = 1,
        label = '_' + label,
        **kwargs,
    )
    ax.plot(
        data,
        markersize = size + .5,
        color = bg,
        linestyle = 'None',
        marker = 's',
        zorder = 2,
        label = '_' + label,
    )
    ax.plot(
        data,
        markersize = size,
        linestyle = 'None',
        marker = marker,
        zorder = 3,
        label = '_' + label,
        color = color,
        # markerfacecolor = 'None',
        markeredgewidth = .1,
        # markeredgecolor = bg,
    )

    ax.plot(
        [],
        label = label,
        markersize = size,
        marker = marker,
        markeredgewidth = .1,
        color = color,
    )

def shade_hls(color, factor: float):
    """
    factor > 1 -> lighter, factor < 1 -> darker
    color: (r,g,b) in 0..1 or 0..255, or hex "#RRGGBB"
    returns (r,g,b) in 0..1
    """
    if isinstance(color, str):
        color = color.lstrip("#")
        r, g, b = (int(color[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = r/255, g/255, b/255
    # else:
    # r, g, b = color
    # if max(color) > 1.0:
        # r, g, b = r/255, g/255, b/255

    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0.0, min(1.0, l * factor))
    return colorsys.hls_to_rgb(h, l, s)

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
        singular_legend: bool = False,
        legend_locs: None | list[list[tuple[float, float]]] = None,
    ) -> list: # list[pyplot.Figure]
    from matplotlib import pyplot
    from matplotlib.ticker import MaxNLocator, FuncFormatter
    import seaborn
    seaborn.set()

    if plot_phase is not None:
        data = [data[plot_phase - 1]]

    experiment_css, colors, markers = get_css(data)
    max_x = max(max(len(hist) for hist in exp.values()) for exp in data)

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

            plus = '+' in cs or '-' in cs

            caller = re.search(r'{.*}', key)
            caller = -1000 if caller is None else -len(caller.group())

            prescript = re.sub(r'\^\d+', '', cs)
            superscript = max([int(x) for x in re.findall(r'\^(\d+)', cs)], default = 0)

            priority = -len(prescript)

            if superscript:
                priority = 0

            if cs.startswith('q'):
                priority = 1

            return group, plus, caller, priority, prescript, superscript, cs

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
            )

            ax = axes[0]
            if plot_V:
                line = ax.plot(hist.assoc, label = key, **plot_options) # type: ignore
                if multiple:
                    ax = axes[1]

            if not hist.compound[0] and plot_alpha and not plot_macknhall:
                ax.plot(hist.alpha, label='α: '+str(key), **plot_options) # type: ignore

            if not hist.compound[0] and plot_macknhall:
                color_mack, color_hall = shade_hls(colors[key], 1.25), shade_hls(colors[key], 0.75)
                if max_x <= 100:
                    plot_around_marker(hist.alpha_mack, ax = ax, label = f'Mack: {key}', char = 'M', color = color_mack)
                    plot_around_marker(hist.alpha_hall, ax = ax, label = f'Hall: {key}', char = 'H', color = color_hall)
                else:
                    ax.plot(hist.alpha_mack, marker = 'o', markersize = 1, markerfacecolor = 'None', label = f'Mack: {key}', color = color_mack)
                    ax.plot(hist.alpha_hall, marker = '^', markersize = 1, label = f'Hall: {key}', color = color_hall)

        longFormat = lambda x, _: f'{x:.0e}' if abs(x) >= 1000 else f'{x:.2f}'

        # Matplotlib makes it hard to start a plot with xticks = [1, t].
        # Instead of fixing the ticks ourselves, we plot in [0, t - 1] and format
        # the ticks to appear as the next number.
        axes[0].set_xlabel('Trial Number', fontsize = 'small', labelpad = 3)
        # axes[0].set_ylim(lowest, highest)
        axes[0].ticklabel_format(useOffset = False, style = 'plain', axis = 'y')
        axes[0].tick_params(axis = 'both', labelsize = 'x-small', pad = 1)
        axes[0].xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x + 1:.0f}'))
        axes[0].xaxis.set_major_locator(MaxNLocator(integer = True, min_n_ticks = 1))
        axes[0].yaxis.set_major_formatter(FuncFormatter(longFormat))

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
            axes[1].yaxis.set_major_formatter(FuncFormatter(longFormat))
            axes[1].yaxis.tick_right()

        if not singular_legend:
            for ax_num, ax in enumerate(axes):
                loc = None
                if legend_locs and legend_locs[phase_num - 1]:
                    loc = legend_locs[phase_num - 1][ax_num]

                PaginatedLegend(ax, loc = loc)

        if phases is not None:
            title = titleify(title, phases, phase_num)
            if title:
                fig.suptitle(title, fontdict = {'family': 'monospace'}, fontsize = 12)

            if len(axes) > 1:
                fig.subplots_adjust(top = .85)

        fig.tight_layout()
        figures.append(fig)

    return figures

class PaginatedLegend:
    def __init__(self, ax, loc = None):
        self.page = 0
        self.loc = loc

        self.handles, self.labels = ax.get_legend_handles_labels()

        if len(self.handles) > 30:
            self.showPage(ax, 0)
            return
        
        properties = dict()
        if len(self.handles) < 6:
            properties = dict(fontsize = 'x-small')
        else:
            properties = dict(fontsize = 7, ncols = 2)

        self.legend = ax.legend(
            self.handles,
            self.labels,
            loc = self.loc or 'best',
            **properties,
        )
        self.num_pages = 1
        self.legend.paginated = False
        self.legend.paginator = None
        self.decorate_legend()

    def showPage(self, ax, page_num):
        from matplotlib.lines import Line2D
        empty = Line2D([], [], linestyle = 'None', marker = None, linewidth = 0)

        size = 15
        line_size = size // 3
        start = size * page_num
        self.num_pages = (len(self.handles) - 1) // size + 1

        h_l = list(zip(self.handles, self.labels))
        lines = [
            [(empty, '◀     Prev')] + h_l[start : start + line_size],
            [(empty, f'Page {1 + page_num}/{self.num_pages}')] + h_l[start + line_size : start + 2 * line_size],
            [(empty, 'Next     ▶')] + h_l[start + 2 * line_size : start + 3 * line_size],
        ]
        lines = [line + [(empty, '')] * max(0, 6 - len(line)) for line in lines]

        handles, labels = map(list, zip(*chain.from_iterable(lines)))
        self.legend = ax.legend(
            handles,
            labels,
            loc = self.loc or 'best',
            fontsize = 7,
            ncol = 3,
            prop = {'family': 'DejaVu Sans', 'size': 7}
        )
        self.decorate_legend()

        self.legend.paginated = True
        self.legend.paginator = self

        texts = self.legend.get_texts()

        prev_id, page_id, next_id = 0, line_size + 1, 2 * (line_size + 1)

        widest_prev = max(x.get_window_extent().x1 for x in texts[prev_id : page_id])
        texts[prev_id].set(
            label = 'Prev',
            fontweight = 'black',
            verticalalignment = 'bottom',
            x = widest_prev / 2 - texts[prev_id].get_window_extent().x1 * (5/4),
        )

        widest_mid = max(x.get_window_extent().x1 for x in texts[page_id + 1 : next_id])
        texts[page_id].set(
            label = '',
            fontfamily = 'serif',
            fontweight = 'semibold',
            verticalalignment = 'bottom',
            x = widest_mid / 2 - texts[page_id].get_window_extent().x1 * (2/3),
        )

        widest_next = max(x.get_window_extent().x1 for x in texts[2 * (line_size + 1) + 1 :])
        texts[next_id].set(
            label = 'Next',
            verticalalignment = 'bottom',
            fontweight = 'black',
            x = widest_next / 2 - texts[next_id].get_window_extent().x1 * (2/3),
        )

        return self.legend

    def decorate_legend(self):
        self.legend.set_draggable(True, use_blit = False, update = 'loc')
        lines, texts = self.legend.get_lines(), self.legend.get_texts()

        for line, text in zip(lines, texts):
            line.set_picker(5)
            text.set_picker(5)
            text.set_label(text.get_text())

def generate_singular_legend(data, plot_stimuli, dpi):
    css, colors, markers = get_css(data)
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
    hide_lines: set[str] = set(),
):
    from matplotlib import pyplot

    if filename is not None:
        filename = filename.removesuffix('.png')

    title = None
    if show_title:
        title = filename
    else:
        phases = None

    # Do not plot lines that are to be hidden.
    data = [
        {cs: phase[cs] for cs in phase.keys() if cs not in hide_lines}
        for phase in data
    ]

    figures = generate_figures(
        data = data,
        phases = phases,
        plot_phase = plot_phase,
        plot_stimuli = plot_stimuli,
        plot_V = plot_V,
        plot_alpha = plot_alpha,
        plot_macknhall = plot_macknhall,
        title = title,
        dpi = dpi,
        singular_legend = singular_legend,
    )

    if singular_legend:
        legend_fig = generate_singular_legend(data, plot_stimuli, dpi)
        legend_fig.set_size_inches(plot_width, .1)
        legend_fig.savefig(f'{filename}_legend.png', bbox_inches = 'tight', pad_inches = 0)

    for phase_num, fig in enumerate(figures, start = plot_phase or 1):
        dep = 1.3
        # if plot_phase is None and phase_num > 1:
        #     fig.axes[0].set_title('')
        #     fig.axes[0].set_ylabel('')
        #     fig.axes[0].set_yticklabels([])

        fig.set_size_inches(plot_width / dep, plot_height / dep)
        # widths = {1: 5, 2: 2, 3: 5}
        # fig.set_size_inches(widths[phase_num] / dep, 2 / dep)
        fig.savefig(f'{filename}_{phase_num}.png', bbox_inches = 'tight')
