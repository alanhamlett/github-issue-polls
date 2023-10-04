# -*- coding: utf-8 -*-
"""
    wakatime.polls.utils
    ~~~~~~~~~~~~~~~~~~~~

    Share utils.
"""

from datetime import datetime, timedelta

import jsonpickle
import pygal
from flask import make_response
from pygal.style import BlueStyle
from pygal.util import ident, swap

from wakatime import r, utils
from wakatime.constants import CACHE_TIMEOUT_ONE_YEAR


def get_poll_image(poll, refresh=False):
    cache_key = f"poll-{poll.id}"
    if not refresh:
        try:
            return jsonpickle.decode(r.get(cache_key)), 200
        except:
            pass

    choices = poll.choices_sorted
    votes = poll.votes
    num_votes = poll.num_votes

    def value_formatter(v):
        plural = "" if int(v) == 1 else "s"
        percent = utils.format_number(v / num_votes * 100) if num_votes else 0
        return f"{v} vote{plural} ({percent}%)"

    style = BlueStyle(background="#fff", plot_background="#fff", label_font_size=16, font_family="monospace")
    chart_options = {
        "margin": 0,
        "margin_left": 20,
        "spacing": 1,
        "show_y_guides": False,
        "show_x_guides": False,
        "show_x_labels": False,
        "show_legend": False,
        "style": style,
        "print_values": True,
        "print_values_position": "bottom",
        "value_formatter": value_formatter,
        "height": (30 * len(choices[:20])) or 200,
    }
    chart = PollChart(**chart_options)
    chart._series_margin = 0
    chart._serie_margin = 0.05

    labels = []
    points = []
    for choice in choices[:20]:
        labels.insert(0, choice)
        points.insert(0, votes.get(choice) or 0)

    chart.x_labels = labels
    chart.add("Votes", points)

    response = make_response(utils.optimize_png(chart.render_to_png()))
    response.headers["Content-Type"] = "image/png"
    response.cache_control.no_cache = True
    response.cache_control.no_store = True
    maxage = 1
    response.cache_control.max_age = maxage
    response.expires = datetime.utcnow() + timedelta(seconds=maxage)

    # cache almost forever, and update cache on new votes
    try:
        r.set(cache_key, jsonpickle.encode(response))
        r.expire(cache_key, time=CACHE_TIMEOUT_ONE_YEAR)
    except:
        pass
    return response, 200


def make_image_response(message):
    chart_options = {
        "title": "",
        "margin": 0,
        "show_y_guides": False,
        "show_x_guides": False,
        "show_x_labels": False,
        "show_legend": False,
        "no_data_text": message,
        "style": pygal.style.DefaultStyle(no_data_font_size=30),
    }
    chart = pygal.HorizontalBar(**chart_options)
    chart.add("", [])

    response = make_response(chart.render_to_png())
    response.headers["Content-Type"] = "image/png"
    response.cache_control.no_cache = True
    response.cache_control.no_store = True
    maxage = 1
    response.cache_control.max_age = maxage
    response.expires = datetime.utcnow() + timedelta(seconds=maxage)

    return response


class PollChart(pygal.HorizontalBar):
    def _tooltip_and_print_values(self, serie_node, serie, parent, i, val, metadata, x, y, width, height):
        transpose = swap if self.horizontal else ident
        x_center, y_center = transpose((x + width / 2, y + height / 2))
        x_top, y_top = transpose((x + width, y + height))
        x_bottom, y_bottom = transpose((x, y))
        if self._dual:
            v = serie.values[i][0]
        else:
            v = serie.values[i]
        sign = -1 if v < self.zero else 1
        self._tooltip_data(parent, val, x_center, y_center, "centered", self._get_x_label(i))

        if self.print_values_position == "top":
            if self.horizontal:
                x = x_bottom + sign * self.style.value_font_size / 2
                y = y_center
            else:
                x = x_center
                y = y_bottom - sign * self.style.value_font_size / 2
        elif self.print_values_position == "bottom":
            if self.horizontal:
                # x = x_top + sign * self.style.value_font_size / 2
                x = x_top + 4 + 5 * len(str(val))
                y = y_center
            else:
                x = x_center
                y = y_top - sign * self.style.value_font_size / 2
        else:
            x = x_center
            y = y_center
        self._static_value(serie_node, val, x, y, metadata, "middle")
