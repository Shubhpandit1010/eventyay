from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIRM_DIALOG_VUE = (
    BASE_DIR
    / 'eventyay'
    / 'webapp'
    / 'schedule-editor'
    / 'src'
    / 'teamshifts-adapter'
    / 'ConfirmDialog.vue'
)


def test_confirm_dialog_accessibility_semantics():
    """Verify ConfirmDialog.vue defines accessible dialog role, aria attributes, and focus attributes."""
    assert CONFIRM_DIALOG_VUE.is_file(), f"File not found: {CONFIRM_DIALOG_VUE}"
    content = CONFIRM_DIALOG_VUE.read_text(encoding='utf-8')

    # Semantic attributes for modal dialogs (ARIA)
    assert 'role="dialog"' in content
    assert 'aria-modal="true"' in content
    assert 'aria-labelledby="ts-confirm-title"' in content
    assert 'h3#ts-confirm-title {{ title }}' in content
    assert 'tabindex="-1"' in content

    # Accessible close button with disabled state during busy operations
    assert 'button.modal-close-btn' in content
    assert ':aria-label="$t(\'Close\')"' in content
    assert ':disabled="busy"' in content


def test_confirm_dialog_escape_key_and_focus_management():
    """Verify ConfirmDialog.vue registers Escape key dismissal and manages focus transitions."""
    content = CONFIRM_DIALOG_VUE.read_text(encoding='utf-8')

    # Keydown listener for Escape dismissal
    assert "e.key === 'Escape'" in content
    assert "e.key === 'Esc'" in content
    assert 'cancel()' in content

    # Guard against dismissal while operation is busy
    assert 'if (props.busy) return' in content
    assert 'if (!props.busy)' in content

    # Scope keydown listener lifecycle strictly to dialog visibility
    assert "window.addEventListener('keydown', onKeydown)" in content
    assert "window.removeEventListener('keydown', onKeydown)" in content
    assert 'onBeforeUnmount' in content

    # Focus management and restoration
    assert 'previousActiveElement = document.activeElement' in content
    assert 'previousActiveElement.focus()' in content
    assert 'nextTick' in content

    # Keyboard focus trap (Tab navigation cycling)
    assert "e.key === 'Tab'" in content
    assert 'querySelectorAll' in content
