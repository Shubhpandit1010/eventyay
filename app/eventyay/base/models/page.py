import html
import json
import re
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import DisallowedHost, ObjectDoesNotExist, ValidationError
from django.db import DatabaseError, models
from django.utils.translation import gettext_lazy as _
from i18nfield.fields import I18nCharField, I18nTextField
from i18nfield.strings import LazyI18nString

from eventyay.base.models import LoggedModel
from eventyay.base.settings import GlobalSettingsObject


SYSTEM_PAGE_SLUGS = {'terms', 'privacy', 'pricing', 'support'}


def validate_footer_url(value: str) -> None:
    """Validate a footer URL or path, rejecting malformed values.

    Raises ValidationError if the URL is malformed (e.g. invalid IPv6 host).
    """
    if not value or not str(value).strip():
        return
    try:
        urlsplit(str(value).strip())
    except ValueError as e:
        raise ValidationError(_('Please enter a valid URL or path.')) from e


def is_content_empty(content: Any) -> bool:
    """Return True if content is None, blank, or contains only empty translations or markup."""
    if not content:
        return True
    if isinstance(content, LazyI18nString):
        data = content.data
    elif isinstance(content, str):
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            data = content
    else:
        data = content

    if data is None or data == '' or (isinstance(data, (list, tuple, set, dict)) and not data):
        return True

    def _has_visible_text(val: Any) -> bool:
        if val is None:
            return False
        s = str(val)
        if '<' in s and '>' in s:
            s = re.sub(r'<[^>]+>', '', s)
            s = html.unescape(s).replace('\xa0', ' ')
        return bool(s.strip())

    if isinstance(data, dict):
        return not any(_has_visible_text(v) for v in data.values())
    if isinstance(data, (list, tuple, set)):
        return not any(_has_visible_text(v) for v in data)
    return not _has_visible_text(data)


def is_system_page_configured(
    slug: str,
    gs=None,
    db_pages_with_content: set[str] | dict[str, Any] | None = None,
) -> bool:
    """Check whether a system page (e.g. terms, privacy, pricing, support) has content configured.

    :param slug: The system page slug.
    :param gs: Optional SettingsSandbox instance.
    :param db_pages_with_content: Optional pre-fetched set or dict of slugs that have non-empty
        content in the database. When provided, avoids database queries.
    :return: True if the page has non-empty text in settings or the database.
    """
    if gs is None:
        gs = GlobalSettingsObject().settings
    custom_text = gs.get(f'footer_page_{slug}_text', as_type=LazyI18nString)
    if not is_content_empty(custom_text):
        return True

    if db_pages_with_content is not None:
        if isinstance(db_pages_with_content, (set, frozenset, list, tuple)):
            return slug in db_pages_with_content
        if isinstance(db_pages_with_content, dict):
            page = db_pages_with_content.get(slug)
            return page is not None and not is_content_empty(page.text)

    try:
        page = Page.objects.filter(slug=slug).first()
        if page and not is_content_empty(page.text):
            return True
    except (DatabaseError, ObjectDoesNotExist, RuntimeError):
        pass
    return False


def _get_allowed_netlocs(request=None) -> set[str]:
    """Resolve allowed network locations and hostnames for the current installation."""
    allowed = set()
    site_url = getattr(settings, 'SITE_URL', '')
    site_netloc = getattr(settings, 'SITE_NETLOC', '')
    if not site_netloc and site_url:
        try:
            site_netloc = urlsplit(site_url).netloc
        except ValueError:
            site_netloc = ''
    if site_netloc:
        allowed.add(site_netloc.lower())
        if ':' in site_netloc:
            allowed.add(site_netloc.split(':')[0].lower())
    if request and hasattr(request, 'get_host'):
        try:
            host = request.get_host()
            if host:
                allowed.add(host.lower())
                if ':' in host:
                    allowed.add(host.split(':')[0].lower())
        except DisallowedHost:
            pass
    return allowed


def is_builtin_page_url(url: str, key: str | None = None, request=None) -> bool:
    """Determine whether a URL targets the built-in system page (e.g. /terms or /page/terms)
    rather than an external or custom destination.
    """
    if not url:
        return False

    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return False

    # Any URL with a non-HTTP(S) scheme (e.g. mailto:, tel:) is external
    if parsed.scheme and parsed.scheme.lower() not in ('http', 'https'):
        return False

    if parsed.netloc:
        allowed = _get_allowed_netlocs(request)
        netloc = parsed.netloc.lower()
        hostname = (parsed.hostname or '').lower()
        if netloc not in allowed and hostname not in allowed:
            return False

    path = parsed.path.strip('/')
    if key:
        return path in (key, f'page/{key}')

    return path in SYSTEM_PAGE_SLUGS or any(path == f'page/{k}' for k in SYSTEM_PAGE_SLUGS)


def is_external_url(url: str, request=None) -> bool:
    """Determine whether a URL points to an external destination outside this installation."""
    if not url:
        return False

    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return False

    if parsed.scheme and parsed.scheme.lower() not in ('http', 'https'):
        return True

    if parsed.netloc:
        allowed = _get_allowed_netlocs(request)
        netloc = parsed.netloc.lower()
        hostname = (parsed.hostname or '').lower()
        return netloc not in allowed and hostname not in allowed

    return False


def get_excluded_system_slugs(gs=None) -> list[str]:
    """Return list of SYSTEM_PAGE_SLUGS that are either disabled or have no configured content.

    Inspects global settings first and queries database content for any missing slugs.
    If a system page is disabled via ``footer_link_{slug}_enabled=False`` or both settings
    and database text are empty, the slug is included in the excluded list.

    :param gs: Optional SettingsSandbox instance.
    :return: List of excluded slug strings.
    """
    try:
        if gs is None:
            gs = GlobalSettingsObject().settings

        excluded_slugs = []
        missing_in_settings = []
        for slug in SYSTEM_PAGE_SLUGS:
            if not gs.get(f'footer_link_{slug}_enabled', as_type=bool, default=True):
                excluded_slugs.append(slug)
                continue
            custom_text = gs.get(f'footer_page_{slug}_text', as_type=LazyI18nString)
            if is_content_empty(custom_text):
                missing_in_settings.append(slug)

        db_configured = set()
        if missing_in_settings:
            try:
                pages = Page.objects.filter(slug__in=missing_in_settings)
                db_configured = {p.slug for p in pages if not is_content_empty(p.text)}
            except (DatabaseError, RuntimeError):
                pass

        for slug in missing_in_settings:
            if slug not in db_configured:
                excluded_slugs.append(slug)

        return excluded_slugs
    except (DatabaseError, RuntimeError):
        return []


def get_visible_system_pages(link_field: str, gs=None):
    """Return Page queryset for system navigation menus, excluding disabled or unconfigured system pages.

    Pages that are not system pages (slug not in SYSTEM_PAGE_SLUGS) and system pages
    whose enabled setting is True and content is configured are kept.

    :param link_field: Name of the boolean field on Page ('link_in_header' or 'link_in_footer').
    :param gs: Optional SettingsSandbox instance.
    :return: Filtered Page queryset.
    """
    filter_kwargs = {'link_in_system': True, link_field: True}
    pages = Page.objects.filter(**filter_kwargs)
    excluded_slugs = get_excluded_system_slugs(gs=gs)
    if excluded_slugs:
        return pages.exclude(slug__in=excluded_slugs)
    return pages


def get_visible_start_page_pages(link_field: str, gs=None):
    """Return Page queryset for website start page navigation menus, excluding disabled or unconfigured system pages.

    Pages that are not system pages (slug not in SYSTEM_PAGE_SLUGS) and system pages
    whose enabled setting is True and content is configured are kept.

    :param link_field: Name of the boolean field on Page ('link_in_header' or 'link_in_footer').
    :param gs: Optional SettingsSandbox instance.
    :return: Filtered Page queryset.
    """
    filter_kwargs = {'link_on_website_start_page': True, link_field: True}
    pages = Page.objects.filter(**filter_kwargs)
    excluded_slugs = get_excluded_system_slugs(gs=gs)
    if excluded_slugs:
        return pages.exclude(slug__in=excluded_slugs)
    return pages


class Page(LoggedModel):
    title = I18nCharField(verbose_name=_('Page title'))
    slug = models.SlugField(
        max_length=150,
        db_index=True,
        verbose_name=_('URL form'),
        help_text=_(
            'This will be used to generate the URL of the page. Please only use latin letters, '
            'numbers, dots and dashes. You cannot change this afterwards.'
        ),
    )
    link_on_website_start_page = models.BooleanField(
        default=False, verbose_name=_('Show link on the website start page')
    )
    link_in_system = models.BooleanField(
        default=True,
        verbose_name=_('Show in header and footer on system pages'),
    )
    link_in_header = models.BooleanField(default=False, verbose_name=_('Show in header menu on all pages'))
    link_in_footer = models.BooleanField(default=False, verbose_name=_('Show in website footer menu on all pages'))
    confirmation_required = models.BooleanField(
        default=False,
        verbose_name=_(
            'Require the user to acknowledge this page before the sign up is created (e.g. for terms of service).'
        ),
    )
    text = I18nTextField(verbose_name=_('Page content'))

    @property
    def has_content(self) -> bool:
        """Return True if the page has non-empty text content."""
        return not is_content_empty(self.text)
