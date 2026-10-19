import json
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError, models
from django.utils.translation import gettext_lazy as _
from i18nfield.fields import I18nCharField, I18nTextField
from i18nfield.strings import LazyI18nString

from eventyay.base.models import LoggedModel
from eventyay.base.settings import GlobalSettingsObject


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
    except (DatabaseError, ObjectDoesNotExist):
        pass
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

