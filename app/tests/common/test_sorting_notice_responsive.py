from pathlib import Path

from bs4 import BeautifulSoup
from django.template import Context, Template
from django.test import RequestFactory


BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES = [
    BASE_DIR / 'eventyay' / 'orga' / 'templates' / 'orga' / 'schedule' / 'room' / 'list.html',
    BASE_DIR / 'eventyay' / 'orga' / 'templates' / 'orga' / 'cfp' / 'track' / 'list.html',
    BASE_DIR / 'eventyay' / 'orga' / 'templates' / 'orga' / 'cfp' / 'submissiontype' / 'list.html',
]

ALERT_CLASSES = (
    'alert alert-info d-flex flex-column flex-sm-row '
    'justify-content-between align-items-sm-center'
)


def test_sorting_notice_templates_contain_responsive_classes():
    """Verify list templates have responsive mobile flex classes and separate link container (#6664)."""
    for template_path in TEMPLATES:
        content = template_path.read_text(encoding='utf-8')
        assert ALERT_CLASSES in content
        assert 'mt-2 mt-sm-0 ml-sm-3 text-nowrap' in content
        assert 'alert-link' in content
        assert 'Reset to manual order' in content


def test_sorting_notice_rendered_dom_structure():
    """Verify sorting alert renders text and reset action in separate containers (#6664)."""
    factory = RequestFactory()
    request = factory.get('/orga/event/schedule/rooms/?sort=name')

    tpl_text = """
    {% load i18n %}
    {% if not can_reorder %}
        <div class="alert alert-info d-flex flex-column flex-sm-row justify-content-between align-items-sm-center">
            <div>
                {% translate 'Manual drag-and-drop reordering is disabled while custom sorting is active.' %}
            </div>
            <div class="mt-2 mt-sm-0 ml-sm-3 text-nowrap">
                <a href="{% querystring sort=None %}" class="alert-link">{% translate 'Reset to manual order' %}</a>
            </div>
        </div>
    {% endif %}
    """
    tpl = Template(tpl_text)
    context = Context({'can_reorder': False, 'request': request})
    context.request = request
    rendered = tpl.render(context)
    soup = BeautifulSoup(rendered, 'html.parser')

    alert = soup.find('div', class_='alert')
    assert alert is not None
    assert 'alert-info' in alert['class']
    assert 'd-flex' in alert['class']
    assert 'flex-column' in alert['class']
    assert 'flex-sm-row' in alert['class']
    assert 'justify-content-between' in alert['class']
    assert 'align-items-sm-center' in alert['class']

    children = alert.find_all('div', recursive=False)
    assert len(children) == 2

    # Text container
    assert 'Manual drag-and-drop reordering is disabled while custom sorting is active.' in children[0].get_text()

    # Action link container
    assert 'mt-2' in children[1]['class']
    assert 'mt-sm-0' in children[1]['class']
    assert 'ml-sm-3' in children[1]['class']
    assert 'text-nowrap' in children[1]['class']

    link = children[1].find('a')
    assert link is not None
    assert 'alert-link' in link['class']
    assert 'Reset to manual order' in link.get_text()
    assert link['href'] == '?'
