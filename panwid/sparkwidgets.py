"""
```sparkwidgets```
========================

A set of sparkline-ish widgets for urwid

This module contains a set of urwid text-like widgets for creating tiny but
hopefully useful sparkline-like visualizations of data.
"""

import urwid
from urwid_utils.palette import *
from collections import deque
import math
import operator
import collections
from dataclasses import dataclass

BLOCK_VERTICAL = [ chr(x) for x in range(0x2581, 0x2589) ]
BLOCK_HORIZONTAL = [ chr(x) for x in range(0x258F, 0x2587, -1) ]

DEFAULT_LABEL_COLOR = "light gray"
DEFAULT_LABEL_COLOR_DARK = "black"
DEFAULT_LABEL_COLOR_LIGHT = "white"

DEFAULT_BACKGROUND_COLOR = "black"

DISTINCT_COLORS_16 = urwid.display_common._BASIC_COLORS[1:]

DISTINCT_COLORS_256 = [
    '#f00', '#080', '#00f', '#d6f', '#0ad', '#f80', '#8f0', '#666',
    '#f88', '#808', '#0fd', '#66f', '#aa8', '#060', '#faf', '#860',
    '#60a', '#600', '#ff8', '#086', '#8a6', '#adf', '#88a', '#f60',
    '#068', '#a66', '#f0a', '#fda'
]

DISTINCT_COLORS_TRUE = [
    '#ff0000', '#008c00', '#0000ff', '#c34fff',
    '#01a5ca', '#ec9d00', '#76ff00', '#595354',
    '#ff7598', '#940073', '#00f3cc', '#4853ff',
    '#a6a19a', '#004301', '#edb7ff', '#8a6800',
    '#6100a3', '#5c0011', '#fff585', '#007b69',
    '#92b853', '#abd4ff', '#7e79a3', '#ff5401',
    '#0a577d', '#a8615c', '#e700b9', '#ffc3a6'
]

COLOR_SCHEMES = {
    "mono": {
        "mode": "mono"
    },
    "rotate_16": {
        "mode": "rotate",
        "colors": DISTINCT_COLORS_16
    },
    "rotate_256": {
        "mode": "rotate",
        "colors": DISTINCT_COLORS_256
    },
    "rotate_true": {
        "mode": "rotate",
        "colors": DISTINCT_COLORS_TRUE
    },
    "signed": {
        "mode": "rules",
        "colors": {
            "nonnegative": "default",
            "negative": "dark red"
        },
        "rules": [
            ( "<", 0, "negative" ),
            ( "else", "nonnegative" ),
        ]
    }
}

def get_palette_entries(
        chart_colors = None,
        label_colors = None
):

    NORMAL_FG_MONO = "white"
    NORMAL_FG_16 = "light gray"
    NORMAL_BG_16 = "black"
    NORMAL_FG_256 = "light gray"
    NORMAL_BG_256 = "black"

    palette_entries = {}

    if not label_colors:
        label_colors = list(set([
            DEFAULT_LABEL_COLOR,
            DEFAULT_LABEL_COLOR_DARK,
            DEFAULT_LABEL_COLOR_LIGHT
        ]))


    if chart_colors:
        colors = chart_colors
    else:
        colors = (urwid.display_common._BASIC_COLORS
                  + DISTINCT_COLORS_256
                  + DISTINCT_COLORS_TRUE )

    fcolors = colors + label_colors
    bcolors = colors

    for fcolor in fcolors:
        if isinstance(fcolor, PaletteEntry):
            fname = fcolor.name
            ffg = fcolor.foreground
            fbg = NORMAL_BG_16
            ffghi = fcolor.foreground_high
            fbghi = NORMAL_BG_256
        else:
            fname = fcolor
            ffg = (fcolor
                  if fcolor in urwid.display_common._BASIC_COLORS
                  else NORMAL_FG_16)
            fbg = NORMAL_BG_16
            ffghi = fcolor
            fbghi = NORMAL_BG_256

        palette_entries.update({
            fname: PaletteEntry(
                name = fname,
                mono = NORMAL_FG_MONO,
                foreground = ffg,
                background = fbg,
                foreground_high = ffghi,
                background_high = fbghi
            ),
        })

        for bcolor in bcolors:

            if isinstance(bcolor, PaletteEntry):
                bname = "%s:%s" %(fname, bcolor.name)
                bfg = ffg
                bbg = bcolor.background
                bfghi = ffghi
                bbghi = bcolor.background_high
            else:
                bname = "%s:%s" %(fname, bcolor)
                bfg = fcolor
                bbg = bcolor
                bfghi = fcolor
                bbghi = bcolor

            palette_entries.update({
                bname: PaletteEntry(
                    name = bname,
                    mono = NORMAL_FG_MONO,
                    foreground = (bfg
                                  if bfg in urwid.display_common._BASIC_COLORS
                                  else NORMAL_BG_16),
                    background = (bbg
                                  if bbg in urwid.display_common._BASIC_COLORS
                                  else NORMAL_BG_16),
                    foreground_high = bfghi,
                    background_high = bbghi
                ),
            })

    return palette_entries



OPERATOR_MAP = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "=": operator.eq,
    "else": lambda a, b: True
}


class SparkWidget(urwid.Text):

    @staticmethod
    def make_rule_function(scheme):

        rules = scheme["rules"]
        def rule_function(value):
            return scheme["colors"].get(
                next(iter(filter(
                    lambda rule: all(
                        OPERATOR_MAP[cond[0]](value, cond[1] if len(cond) > 1 else None)
                        for cond in [rule]
                    ), scheme["rules"]
                )))[-1]
            )
        return rule_function


    @staticmethod
    def normalize(v, a, b, scale_min, scale_max):

        # if not scale_min:
        #     scale_min = v_min

        # if not scale_max:
        #     scale_max = v_max

        if scale_max == scale_min:
            return v
        return max(
            a,
            min(
                b,
                (((v - scale_min) / (scale_max - scale_min) ) * (b - a) + a)
            )
        )


    def parse_scheme(self, scheme):

        if isinstance(scheme, dict):
            color_scheme = scheme
        else:
            try:
                color_scheme = COLOR_SCHEMES[scheme]
            except:
                raise Exception("Unknown color scheme: %s" %(scheme))

        mode = color_scheme["mode"]
        if mode == "mono":
            return None

        elif mode == "rotate":
            return deque(color_scheme["colors"])

        elif mode == "rules":
            return self.make_rule_function(color_scheme)

        else:
            raise Exception("Unknown color scheme mode: %s" %(mode))

    @property
    def current_color(self):

        return self.colors[0]

    def next_color(self):
        if not self.colors:
            return
        self.colors.rotate(-1)
        return self.current_color

    def get_color(self, item):
        if not self.colors:
            color = None
        elif callable(self.colors):
            color = self.colors(item)
        elif isinstance(self.colors, collections.Iterable):
            color = self.current_color
            self.next_color()
            return color
        else:
            raise Exception(self.colors)

        return color


class SparkColumnWidget(SparkWidget):
    """
    A sparkline-ish column widget for Urwid.

    Given a list of numeric values, this widget will draw a small text-based
    vertical bar graph of the values, one character per value.  Column segments
    can be colorized according to a color scheme or by assigning each
    value a color.

    :param items: A list of items to be charted in the widget.  Items can be
    either numeric values or tuples, the latter of which must be of the form
    ('attribute', value) where attribute is an urwid text attribute and value
    is a numeric value.

    :param color_scheme: A string or dictionary containing the name of or
    definition of a color scheme for the widget.

    :param underline: one of None, "negative", or "min", specifying values that
    should be marked in the chart.  "negative" shows negative values as little
    dots at the bottom of the chart, while "min" uses a unicode combining
    three dots character to indicate minimum values.  Results of this and the
    rest of these parameters may not look great with all terminals / fonts,
    so if this looks weird, don't use it.

    :param overline: one of None or "max" specfying values that should be marked
    in the chart.  "max" draws three dots above the max value.  See underline
    description for caveats.

    :param scale_min: Set a minimum scale for the chart.  By default, the range
    of the chart's Y axis will expand to show all values, but this parameter
    can be used to restrict or expand the Y-axis.

    :param scale_max: Set the maximum for the Y axis. -- see scale_min.
    """

    chars = BLOCK_VERTICAL

    def __init__(self, items,
                 color_scheme = "mono",
                 scale_min = None,
                 scale_max = None,
                 underline = None,
                 overline = None,
                 *args, **kwargs):

        self.items = items
        self.colors = self.parse_scheme(color_scheme)

        self.underline = underline
        self.overline = overline

        self.values = [ i[1] if isinstance(i, tuple) else i for i in self.items ]

        v_min = min(self.values)
        v_max = max(self.values)


        def item_to_glyph(item):

            color = None

            if isinstance(item, tuple):
                color = item[0]
                value = item[1]
            else:
                color = self.get_color(item)
                value = item

            if self.underline == "negative" and value < 0:
                glyph = " \N{COMBINING DOT BELOW}"
            else:


                # idx = scale_value(value, scale_min=scale_min, scale_max=scale_max)
                idx = self.normalize(
                    value, 0, len(self.chars)-1,
                    scale_min if scale_min else v_min,
                    scale_max if scale_max else v_max)

                glyph = self.chars[int(round(idx))]

                if self.underline == "min" and value == v_min:
                    glyph = "%s\N{COMBINING TRIPLE UNDERDOT}" %(glyph)

                if self.overline == "max" and value == v_max:
                    glyph = "%s\N{COMBINING THREE DOTS ABOVE}" %(glyph)

            if color:
                return (color, glyph)
            else:
                return glyph

        self.sparktext = [
            item_to_glyph(i)
            for i in self.items
        ]
        super(SparkColumnWidget, self).__init__(self.sparktext, *args, **kwargs)


# https://stackoverflow.com/a/20054616
def proportional(nseats, votes):
    """assign n seats proportionaly to votes using Hagenbach-Bischoff quota
    :param nseats: int number of seats to assign
    :param votes: iterable of int or float weighting each party
    :result: list of ints seats allocated to each party
    """
    if sum(votes) == 0:
        votes = [1 for vote in votes]
    quota=sum(votes)/(1.+nseats) #force float
    frac=[vote/quota for vote in votes]
    res=[int(f) for f in frac]
    n=nseats-sum(res) #number of seats remaining to allocate
    if n==0: return res #done
    if n<0: return [min(x,nseats) for x in res] # see siamii's comment
    #give the remaining seats to the n parties with the largest remainder
    remainders=[ai-bi for ai,bi in zip(frac,res)]
    limit=sorted(remainders,reverse=True)[n-1]
    #n parties with remainter larger than limit get an extra seat
    for i,r in enumerate(remainders):
        if r>=limit:
            res[i]+=1
            n-=1 # attempt to handle perfect equality
            if n==0: return res #done
    raise #should never happen


@dataclass
class SparkBarItem:
    value: int
    label: str = None
    fcolor: str = None
    bcolor: str = None
    align: str = "<"

class SparkBarWidget(SparkWidget):
    """
    A sparkline-ish horizontal stacked bar widget for Urwid.

    This widget graphs a set of values in a horizontal bar style.

    :param items: A list of items to be charted in the widget.  Items can be
    either numeric values or tuples, the latter of which must be of the form
    ('attribute', value) where attribute is an urwid text attribute and value
    is a numeric value.

    :param width: Width of the widget in characters.

    :param color_scheme: A string or dictionary containing the name of or
    definition of a color scheme for the widget.
    """

    chars = BLOCK_HORIZONTAL

    def __init__(self, items, width,
                 color_scheme="mono",
                 label_color=None,
                 min_width=None,
                 fit_label=False,
                 normalize=None,
                 *args, **kwargs):

        self.items = [
            i if isinstance(i, SparkBarItem) else SparkBarItem(i)
            for i in items
        ]

        self.width = width
        self.label_color = label_color
        self.min_width = min_width
        self.fit_label = fit_label

        values = None
        total = None

        if normalize:
            values = [ item.value for item in self.items ]
            v_min = min(values)
            v_max = max(values)
            values = [
                int(self.normalize(v,
                                   normalize[0], normalize[1],
                                   v_min, v_max))
                for v in values
            ]
            for i, v in enumerate(values):
                self.items[i].value = v


        filtered_items = [i for i in self.items]

        # ugly brute force method to eliminate values too small to display
        while True:
            values = [i.value for i in filtered_items]

            if not len(values):
                raise Exception(self.items)
            total = sum(values)
            v_min = min(values)
            v_max = max(values)
            charwidth = total / self.width
            try:
                i = next(iter(filter(
                    lambda i: not (self.min_width or self.fit_label) and i.value < charwidth,
                    filtered_items)))
                filtered_items.remove(i)
            except StopIteration:
                break


        self.colors = self.parse_scheme(color_scheme)

        charwidth = total / self.width
        stepwidth = charwidth / len(self.chars)

        self.sparktext = []

        position = 0
        carryover = 0
        nchars = len(self.chars)
        lastcolor = None

        bars = proportional(self.width, [i.value for i in filtered_items])

        if self.min_width:
            last = None
            while any(i < self.min_width for i in bars):
                if bars == last:
                    break
                last = [b for b in bars]
                smallest = min(bars)
                largest = max(bars)
                bars[bars.index(smallest)] += 1
                bars[bars.index(largest)] -= 1

        for i, item in enumerate(filtered_items):

            rangechars = displaychars = bars[i]
            text = ""
            label = None
            label_align = "<"

            if item.label is not None:
                try:
                    pct = int(round(v/total*100, 0))
                except:
                    pct = ""
                text += str(item.label).format(
                    value=item.value,
                    pct=pct
                )

            # if self.min_width:
            #     displaychars = max(displaychars, self.min_width)

            # if self.fit_label:
            #     displaychars = max(displaychars, len(text))

            if text and displaychars:
                chars = "{:{a}{m}.{m}}{lastchar}".format(
                    "{text:.{n}}".format(
                        text=text,
                        # n=displaychars-1
                        n=max(min(len(text), displaychars-1), 0),
                    ),
                    m=max((displaychars-1), 0),
                    a=item.align or "<",
                    lastchar="\N{HORIZONTAL ELLIPSIS}"
                    if len(text) > displaychars
                    else text[displaychars-1]
                    if len(text) == displaychars
                    else " "
                )
            else:
                chars = " "*rangechars

            position += displaychars*charwidth

            self.sparktext.append(
                ("%s:%s" %(
                    item.fcolor or self.label_color or DEFAULT_LABEL_COLOR,
                    item.bcolor or self.current_color), chars
                 )
            )
            self.next_color()



        if not self.sparktext:
            self.sparktext = ""
        super(SparkBarWidget, self).__init__(self.sparktext, *args, **kwargs)

__all__ = ["SparkColumnWidget", "SparkBarWidget"]
