from pathlib import Path


def test_password_toggle_css_hides_edge_reveal_controls() -> None:
    """Verify password_toggle.css hides browser-native password reveal and clear buttons."""
    css_path = Path(__file__).resolve().parents[2] / 'eventyay' / 'static' / 'common' / 'css' / 'password_toggle.css'
    content = css_path.read_text(encoding='utf-8')

    assert '::-ms-reveal' in content
    assert '::-ms-clear' in content
    assert 'display: none;' in content


def test_forms_css_hides_edge_reveal_controls() -> None:
    """Verify _forms.css hides browser-native password reveal and clear buttons for password wrappers."""
    css_path = Path(__file__).resolve().parents[2] / 'eventyay' / 'static' / 'common' / 'css' / '_forms.css'
    content = css_path.read_text(encoding='utf-8')

    assert '.password-input-wrapper input::-ms-reveal' in content
    assert '.password-input-wrapper input::-ms-clear' in content
    assert 'display: none;' in content


def test_auth_scss_hides_edge_reveal_controls() -> None:
    """Verify auth.scss hides browser-native password reveal and clear buttons."""
    scss_path = Path(__file__).resolve().parents[2] / 'eventyay' / 'static' / 'pretixcontrol' / 'scss' / 'auth.scss'
    content = scss_path.read_text(encoding='utf-8')

    assert 'input[type="password"]::-ms-reveal' in content
    assert 'input[type="password"]::-ms-clear' in content
    assert 'display: none;' in content


def test_auth_base_template_links_password_toggle_css() -> None:
    """Verify the auth base template links password_toggle.css."""
    template_path = (
        Path(__file__).resolve().parents[2]
        / 'eventyay'
        / 'eventyay_common'
        / 'templates'
        / 'eventyay_common'
        / 'auth'
        / 'base.html'
    )
    content = template_path.read_text(encoding='utf-8')

    assert 'common/css/password_toggle.css' in content


def test_account_base_template_links_password_toggle_css() -> None:
    """Verify the account base Jinja template links password_toggle.css."""
    template_path = (
        Path(__file__).resolve().parents[2]
        / 'eventyay'
        / 'jinja-templates'
        / 'account'
        / 'base.jinja'
    )
    content = template_path.read_text(encoding='utf-8')

    assert 'common/css/password_toggle.css' in content
