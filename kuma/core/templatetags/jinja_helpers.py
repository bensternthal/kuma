import datetime
import HTMLParser
import json
import urllib

import bleach
import jinja2
import pytz
from babel import dates, localedata, numbers
from django.conf import settings
from django.contrib.messages.storage.base import LEVEL_TAGS
from django.contrib.staticfiles.storage import staticfiles_storage
from django.template import defaultfilters
from django.template.loader import get_template
from django.utils.encoding import force_text
from django.utils.html import strip_tags
from django.utils.timezone import get_default_timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext
from django_jinja import library
from pytz import timezone
from soapbox.models import Message
from statici18n.templatetags.statici18n import statici18n
from urlobject import URLObject

from ..exceptions import DateTimeFormatError
from ..urlresolvers import reverse, split_path
from ..utils import urlparams


htmlparser = HTMLParser.HTMLParser()


# Yanking filters from Django.
library.filter(defaultfilters.linebreaksbr)
library.filter(strip_tags)
library.filter(defaultfilters.timesince)
library.filter(defaultfilters.truncatewords)
library.global_function(statici18n)

library.filter(urlparams)


@library.filter
def paginator(pager):
    """Render list of pages."""
    return Paginator(pager).render()


@library.global_function
def url(viewname, *args, **kwargs):
    """Helper for Django's ``reverse`` in templates."""
    locale = kwargs.pop('locale', None)
    return reverse(viewname, args=args, kwargs=kwargs, locale=locale)


class Paginator(object):

    def __init__(self, pager):
        self.pager = pager

        self.max = 10
        self.span = (self.max - 1) / 2

        self.page = pager.number
        self.num_pages = pager.paginator.num_pages
        self.count = pager.paginator.count

        pager.page_range = self.range()
        pager.dotted_upper = self.num_pages not in pager.page_range
        pager.dotted_lower = 1 not in pager.page_range

    def range(self):
        """Return a list of page numbers to show in the paginator."""
        page, total, span = self.page, self.num_pages, self.span
        if total < self.max:
            lower, upper = 0, total
        elif page < span + 1:
            lower, upper = 0, span * 2
        elif page > total - span:
            lower, upper = total - span * 2, total
        else:
            lower, upper = page - span, page + span - 1
        return range(max(lower + 1, 1), min(total, upper) + 1)

    def render(self):
        c = {'pager': self.pager, 'num_pages': self.num_pages,
             'count': self.count}
        t = get_template('includes/paginator.html').render(c)
        return jinja2.Markup(t)


@library.filter
def timesince(d, now=None):
    """Take two datetime objects and return the time between d and now as a
    nicely formatted string, e.g. "10 minutes".  If d is None or occurs after
    now, return ''.

    Units used are years, months, weeks, days, hours, and minutes. Seconds and
    microseconds are ignored.  Just one unit is displayed.  For example,
    "2 weeks" and "1 year" are possible outputs, but "2 weeks, 3 days" and "1
    year, 5 months" are not.

    Adapted from django.utils.timesince to have better i18n (not assuming
    commas as list separators and including "ago" so order of words isn't
    assumed), show only one time unit, and include seconds.

    """
    if d is None:
        return u''
    chunks = [
        (60 * 60 * 24 * 365, lambda n: ungettext('%(number)d year ago',
                                                 '%(number)d years ago', n)),
        (60 * 60 * 24 * 30, lambda n: ungettext('%(number)d month ago',
                                                '%(number)d months ago', n)),
        (60 * 60 * 24 * 7, lambda n: ungettext('%(number)d week ago',
                                               '%(number)d weeks ago', n)),
        (60 * 60 * 24, lambda n: ungettext('%(number)d day ago',
                                           '%(number)d days ago', n)),
        (60 * 60, lambda n: ungettext('%(number)d hour ago',
                                      '%(number)d hours ago', n)),
        (60, lambda n: ungettext('%(number)d minute ago',
                                 '%(number)d minutes ago', n)),
        (1, lambda n: ungettext('%(number)d second ago',
                                '%(number)d seconds ago', n))]
    if not now:
        if d.tzinfo:
            now = datetime.datetime.now(get_default_timezone())
        else:
            now = datetime.datetime.now()

    # Ignore microsecond part of 'd' since we removed it from 'now'
    delta = now - (d - datetime.timedelta(0, 0, d.microsecond))
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since <= 0:
        # d is in the future compared to now, stop processing.
        return u''
    for i, (seconds, name) in enumerate(chunks):
        count = since // seconds
        if count != 0:
            break
    return name(count) % {'number': count}


@library.filter
def yesno(boolean_value):
    return jinja2.Markup(_(u'Yes') if boolean_value else _(u'No'))


@library.filter
def entity_decode(str):
    """Turn HTML entities in a string into unicode."""
    return htmlparser.unescape(str)


@library.global_function
def page_title(title):
    return u'%s | MDN' % title


@library.filter
def level_tag(message):
    return jinja2.Markup(force_text(LEVEL_TAGS.get(message.level, ''),
                                    strings_only=True))


@library.filter
def isotime(t):
    """Date/Time format according to ISO 8601"""
    if not hasattr(t, 'tzinfo'):
        return
    return _append_tz(t).astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_tz(t):
    tz = pytz.timezone(settings.TIME_ZONE)
    return tz.localize(t)


@library.global_function
def thisyear():
    """The current year."""
    return jinja2.Markup(datetime.date.today().year)


@library.filter
def cleank(txt):
    """Clean and link some user-supplied text."""
    return jinja2.Markup(bleach.linkify(bleach.clean(txt)))


@library.filter
def urlencode(txt):
    """Url encode a path."""
    return urllib.quote_plus(txt.encode('utf8'))


@library.filter
def jsonencode(data):
    return jinja2.Markup(json.dumps(data))


@library.global_function
def get_soapbox_messages(url):
    _, path = split_path(url)
    return Message.objects.match(path)


@library.global_function
def get_webfont_attributes(request):
    """
    Return data attributes based on assumptions about if user has them cached
    """
    if not request:
        return ''
    assume_loaded = 'true'
    if request.META.get('HTTP_PRAGMA') == 'no-cache':
        assume_loaded = 'false'
    elif request.META.get('HTTP_CACHE_CONTROL') == 'no-cache':
        assume_loaded = 'false'
    elif request.COOKIES.get('ffo', 'false') == 'true':
        assume_loaded = 'true'
    else:
        assume_loaded = 'false'

    font_names = ['opensanslight', 'opensans']
    font_attributes = ''
    for font_name in font_names:
        font_attributes += ' data-ffo-' + font_name + '=' + assume_loaded + ''

    return font_attributes


@library.global_function
@library.render_with('core/elements/soapbox_messages.html')
def soapbox_messages(soapbox_messages):
    return {'soapbox_messages': soapbox_messages}


@library.global_function
def add_utm(url_, campaign, source='developer.mozilla.org', medium='email'):
    """Add the utm_* tracking parameters to a URL."""
    url_obj = URLObject(url_).add_query_params({
        'utm_campaign': campaign,
        'utm_source': source,
        'utm_medium': medium})
    return str(url_obj)


def _babel_locale(locale):
    """Return the Babel locale code, given a normal one."""
    # Babel uses underscore as separator.
    return locale.replace('-', '_')


def _contextual_locale(context):
    """Return locale from the context, falling back to a default if invalid."""
    locale = context['request'].LANGUAGE_CODE
    if not localedata.exists(locale):
        locale = settings.LANGUAGE_CODE
    return locale


def format_date_value(value, tzvalue, locale, format):
    if format == 'shortdatetime':
        # Check if the date is today
        if value.toordinal() == datetime.date.today().toordinal():
            formatted = dates.format_time(tzvalue, format='short',
                                          locale=locale)
            return _(u'Today at %s') % formatted
        else:
            return dates.format_datetime(tzvalue, format='short',
                                         locale=locale)
    elif format == 'longdatetime':
        return dates.format_datetime(tzvalue, format='long', locale=locale)
    elif format == 'date':
        return dates.format_date(tzvalue, locale=locale)
    elif format == 'time':
        return dates.format_time(tzvalue, locale=locale)
    elif format == 'datetime':
        return dates.format_datetime(tzvalue, locale=locale)
    else:
        # Unknown format
        raise DateTimeFormatError


@library.global_function
@jinja2.contextfunction
def datetimeformat(context, value, format='shortdatetime', output='html'):
    """
    Returns date/time formatted using babel's locale settings. Uses the
    timezone from settings.py
    """
    if not isinstance(value, datetime.datetime):
        if isinstance(value, datetime.date):
            # Turn a date into a datetime
            value = datetime.datetime.combine(value,
                                              datetime.datetime.min.time())
        else:
            # Expecting datetime value
            raise ValueError

    default_tz = timezone(settings.TIME_ZONE)
    tzvalue = default_tz.localize(value)

    user = context['request'].user
    try:
        if user.is_authenticated() and user.timezone:
            user_tz = timezone(user.timezone)
            tzvalue = user_tz.normalize(tzvalue.astimezone(user_tz))
    except AttributeError:
        pass

    locale = _babel_locale(_contextual_locale(context))

    try:
        formatted = format_date_value(value, tzvalue, locale, format)
    except KeyError:
        # Babel sometimes stumbles over missing formatters in some locales
        # e.g. bug #1247086
        # we fall back formatting the value with the default language code
        formatted = format_date_value(value, tzvalue,
                                      _babel_locale(settings.LANGUAGE_CODE),
                                      format)

    if output == 'json':
        return formatted
    return jinja2.Markup('<time datetime="%s">%s</time>' %
                         (tzvalue.isoformat(), formatted))


@library.global_function
@jinja2.contextfunction
def number(context, number):
    """
    Return the localized representation of an integer or decimal.

    For None, print nothing.
    """
    if number is None:
        return ''
    locale = _babel_locale(_contextual_locale(context))
    return numbers.format_decimal(number, locale=locale)


@library.global_function
def static(path):
    return staticfiles_storage.url(path)
