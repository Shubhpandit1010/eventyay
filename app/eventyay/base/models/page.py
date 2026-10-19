import json
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError, models
from django.utils.translation import gettext_lazy as _
from i18nfield.fields import I18nCharField, I18nTextField
from i18nfield.strings import LazyI18nString

from eventyay.base.models import LoggedModel
from eventyay.base.settings import GlobalSettingsObject


SYSTEM_PAGE_SLUGS = {'terms', 'privacy', 'pricing', 'support'}


def is_content_empty(content: Any) -> bool:
    """Return True if content is None, blank, or contains only empty translations."""
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

    if isinstance(data, dict):
        return not any(str(v).strip() for v in data.values() if v is not None)
    if isinstance(data, str):
        return not data.strip()
    return not str(data).strip()


def is_system_page_configured(slug: str, gs=None) -> bool:
    """Check whether a system page (e.g. terms, privacy, pricing, support) has content configured."""
    if gs is None:
        gs = GlobalSettingsObject().settings
    custom_text = gs.get(f'footer_page_{slug}_text', as_type=LazyI18nString)
    if not is_content_empty(custom_text):
        return True
    try:
        page = Page.objects.filter(slug=slug).first()
        if page and not is_content_empty(page.text):
            return True
    except (DatabaseError, ObjectDoesNotExist, RuntimeError):
        pass
    return False


def is_builtin_page_url(url: str, key: str | None = None, request=None) -> bool:
    """Determine whether a URL targets the built-in system page (e.g. /terms or /page/terms)
    rather than an external or custom destination.
    """
    if not url:
        return False

    parsed = urlsplit(url.strip())
    # Any URL with a non-HTTP(S) scheme (e.g. mailto:, tel:) is external
    if parsed.scheme and parsed.scheme.lower() not in ('http', 'https'):
        return False

    if parsed.netloc:
        allowed_netlocs = set()
        site_url = getattr(settings, 'SITE_URL', '')
        site_netloc = getattr(settings, 'SITE_NETLOC', '')
        if not site_netloc and site_url:
            site_netloc = urlsplit(site_url).netloc
        if site_netloc:
            allowed_netlocs.add(site_netloc.lower())
        if request and hasattr(request, 'get_host'):
            try:
                allowed_netlocs.add(request.get_host().lower())
            except Exception:
                pass
        if parsed.netloc.lower() not in allowed_netlocs:
            return False

    path = parsed.path.strip('/')
    if key:
        return path in (key, f'page/{key}')

    return path in SYSTEM_PAGE_SLUGS or any(path == f'page/{k}' for k in SYSTEM_PAGE_SLUGS)


def is_external_url(url: str, request=None) -> bool:
    """Determine whether a URL points to an external destination outside this installation."""
    if not url:
        return False

    parsed = urlsplit(url.strip())
    if parsed.scheme and parsed.scheme.lower() not in ('http', 'https'):
        return True

    if parsed.netloc:
        allowed_netlocs = set()
        site_url = getattr(settings, 'SITE_URL', '')
        site_netloc = getattr(settings, 'SITE_NETLOC', '')
        if not site_netloc and site_url:
            site_netloc = urlsplit(site_url).netloc
        if site_netloc:
            allowed_netlocs.add(site_netloc.lower())
        if request and hasattr(request, 'get_host'):
            try:
                allowed_netlocs.add(request.get_host().lower())
            except Exception:
                pass
        return parsed.netloc.lower() not in allowed_netlocs

    return False


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
        return not is_content_empty(self.text)

