from unittest.mock import MagicMock, patch

from eventyay.base.services.vouchers import vouchers_send


def test_vouchers_send_preserves_existing_comment():
    """Verify vouchers_send appends sent-to note to existing voucher comments without overwriting (#6645)."""
    mock_event = MagicMock()
    mock_event.settings.locale = 'en'

    mock_voucher = MagicMock()
    mock_voucher.id = 1
    mock_voucher.code = 'VOUCHER1'
    mock_voucher.tag = None
    mock_voucher.comment = 'Reserved for keynote speaker'

    mock_user = MagicMock()

    with (
        patch('eventyay.base.services.vouchers.Voucher.objects.filter') as mock_v_filter,
        patch('eventyay.base.services.vouchers.Voucher.objects.bulk_update') as mock_bulk_update,
        patch('eventyay.base.services.vouchers.User.objects.get', return_value=mock_user),
        patch('eventyay.base.services.vouchers.LogEntry.objects.bulk_create'),
        patch('eventyay.base.services.vouchers.get_email_context', return_value={}),
        patch('eventyay.base.services.vouchers.mail'),
    ):
        mock_v_filter.return_value.order_by.return_value = [mock_voucher]

        vouchers_send(
            event=mock_event,
            vouchers=[1],
            subject='Your voucher',
            message='Here is your voucher: {voucher_list}',
            recipients=[{'email': 'speaker@example.com', 'number': 1}],
            user=42,
        )

        assert mock_voucher.comment == (
            'Reserved for keynote speaker\n\n'
            'The voucher has been sent to speaker@example.com.'
        )
        mock_bulk_update.assert_called_once_with([mock_voucher], fields=['comment', 'tag'], batch_size=500)


def test_vouchers_send_sets_note_when_no_prior_comment():
    """Verify vouchers_send sets sent-to note without leading newlines when no comment exists (#6645)."""
    mock_event = MagicMock()
    mock_event.settings.locale = 'en'

    mock_voucher = MagicMock()
    mock_voucher.id = 2
    mock_voucher.code = 'VOUCHER2'
    mock_voucher.tag = None
    mock_voucher.comment = None

    mock_user = MagicMock()

    with (
        patch('eventyay.base.services.vouchers.Voucher.objects.filter') as mock_v_filter,
        patch('eventyay.base.services.vouchers.Voucher.objects.bulk_update') as mock_bulk_update,
        patch('eventyay.base.services.vouchers.User.objects.get', return_value=mock_user),
        patch('eventyay.base.services.vouchers.LogEntry.objects.bulk_create'),
        patch('eventyay.base.services.vouchers.get_email_context', return_value={}),
        patch('eventyay.base.services.vouchers.mail'),
    ):
        mock_v_filter.return_value.order_by.return_value = [mock_voucher]

        vouchers_send(
            event=mock_event,
            vouchers=[2],
            subject='Your voucher',
            message='Here is your voucher: {voucher_list}',
            recipients=[{'email': 'attendee@example.com', 'number': 1}],
            user=42,
        )

        assert mock_voucher.comment == 'The voucher has been sent to attendee@example.com.'
        mock_bulk_update.assert_called_once_with([mock_voucher], fields=['comment', 'tag'], batch_size=500)


def test_vouchers_send_multiple_recipients():
    """Verify vouchers_send handles multiple recipients and updates each voucher's comment correctly (#6645)."""
    mock_event = MagicMock()
    mock_event.settings.locale = 'en'

    v1 = MagicMock(id=1, code='CODE1', tag=None, comment='Existing note')
    v2 = MagicMock(id=2, code='CODE2', tag=None, comment='')

    mock_user = MagicMock()

    with (
        patch('eventyay.base.services.vouchers.Voucher.objects.filter') as mock_v_filter,
        patch('eventyay.base.services.vouchers.Voucher.objects.bulk_update') as mock_bulk_update,
        patch('eventyay.base.services.vouchers.User.objects.get', return_value=mock_user),
        patch('eventyay.base.services.vouchers.LogEntry.objects.bulk_create'),
        patch('eventyay.base.services.vouchers.get_email_context', return_value={}),
        patch('eventyay.base.services.vouchers.mail'),
    ):
        mock_v_filter.return_value.order_by.return_value = [v1, v2]

        vouchers_send(
            event=mock_event,
            vouchers=[1, 2],
            subject='Your vouchers',
            message='Here are your vouchers: {voucher_list}',
            recipients=[
                {'email': 'user1@example.com', 'number': 1},
                {'email': 'user2@example.com', 'number': 1},
            ],
            user=1,
        )

        # vouchers.pop() pops from the end, so v2 is user1 and v1 is user2
        assert 'The voucher has been sent to user1@example.com.' in v2.comment
        assert not v2.comment.startswith('\n')
        assert v1.comment == 'Existing note\n\nThe voucher has been sent to user2@example.com.'
        assert mock_bulk_update.call_count == 2
