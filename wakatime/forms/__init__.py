# -*- coding: utf-8 -*-
"""
    wakatime.forms
    ~~~~~~~~~~~~~~

    Forms for validating user input.
"""


from collections import Counter

import wtforms_json
from wtforms import Form, widgets
from wtforms.fields import Field
from wtforms.validators import (
    DataRequired,
    Length,
    Optional,
    StopValidation,
)

from wakatime import utils


wtforms_json.init()


def monkey_patch_optional_init(func):
    """
    Monkey patches Optional.__init__ to accept nullable and blank kwargs.
    """

    def init(self, strip_whitespace=True, nullable=True, blank=True, message=None):
        if strip_whitespace:
            self.string_check = lambda s: s.strip()
        else:
            self.string_check = lambda s: s
        self.nullable = nullable
        self.blank = blank
        self.message = message

    return init


def monkey_patch_optional_call(func):
    """
    Monkey patches Optional.__call__ to handle nullable and blank.
    """

    def call(self, form, field, *args, **kwargs):
        try:
            func(self, form, field, *args, **kwargs)
        except StopValidation:
            if hasattr(field, "is_missing") and field.is_missing:
                raise StopValidation()

            if self.message is None:
                message = field.gettext("This field is required.")
            else:
                message = self.message

            if field.raw_data is None:
                if self.nullable:
                    raise StopValidation()
                elif self.message is None:
                    message = field.gettext("This field can not be null.")

            else:
                is_blank = isinstance(field.raw_data[0], (str, bytes)) and not self.string_check(field.raw_data[0])
                if is_blank and self.blank:
                    raise StopValidation()
                elif self.message is None:
                    message = field.gettext("This field can not be blank.")

            raise StopValidation(message)

    return call


Optional.__init__ = monkey_patch_optional_init(Optional.__init__)
Optional.__call__ = monkey_patch_optional_call(Optional.__call__)


class StringField(Field):
    widget = widgets.TextInput()

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = valuelist[0]
        else:
            self.data = None

    def _value(self):
        return str(self.data) if self.data is not None else None


""" Utility Functions
"""


def strip_multiline(data, remove_empty_items=None, remove_duplicates=None):
    try:
        seen = Counter()
        text = []
        for line in data.split("\n"):
            item = utils.safe_unicode(utils.replace_whitespace(utils.remove_nulls(line.strip()))).strip()
            if remove_empty_items and not item:
                continue
            if remove_duplicates:
                if item in seen:
                    continue
                seen[item] += 1
            text.append(item)
        return "\n".join(text)
    except:
        return None


def strip_multiline_removing_empty_and_dupe_items(data):
    return strip_multiline(data, remove_empty_items=True, remove_duplicates=True)


""" Forms
"""


class PollForm(Form):
    choices = StringField(validators=[DataRequired(), Length(min=1)], filters=[strip_multiline_removing_empty_and_dupe_items])
