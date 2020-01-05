"""template monkey patching"""

from datetime import date, timedelta
from homeassistant.helpers.template import TemplateEnvironment


def nth_day(year, month, dow, week):
    """Determine the nth weekday of a month."""
    date_time = date(year, month, 1)
    delta = 0
    if date_time.weekday() <= dow:
        delta = dow - date_time.weekday()
    else:
        delta = (7 - date_time.weekday()) + dow

    date_time = date(year, month, 1 + 7 * (week - 1))
    return date_time + timedelta(days=delta)


old_init = TemplateEnvironment.__init__


def new_init(self, hass):
    """Initialize the jinja2 environment."""
    old_init(self, hass)
    self.globals["nth_day"] = nth_day


TemplateEnvironment.__init__ = new_init

