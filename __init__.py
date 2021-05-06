"""template monkey patching"""
from datetime import date, timedelta
from os import path
import ssl

from homeassistant.helpers.template import TemplateEnvironment
from homeassistant.util import ssl as hassl


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

def new_init(self, hass, limited=False, strict=False):
    """Initialize the jinja2 environment."""
    old_init(self, hass, limited, strict)
    self.globals["nth_day"] = nth_day


TemplateEnvironment.__init__ = new_init

old_client_context = hassl.client_context


def new_client_context() -> ssl.SSLContext:
    context = old_client_context()
    caFile = f"{path.dirname(__file__)}/../ca-cert.pem"
    if path.exists(caFile):
        context.load_verify_locations(caFile)
    return context


hassl.client_context = new_client_context
