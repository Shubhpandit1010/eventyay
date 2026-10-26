import datetime
from unittest.mock import patch

import pytest
from django_scopes import scope, scopes_disabled

from eventyay.base.models import Event, Organizer, User, Voucher
from eventyay.base.services.vouchers import vouchers_send


@pytest.fixture
def env():
    with scopes_disabled():
        organizer = Organizer.objects.create(name='CCC', slug='ccc-vouchers-send')
        event = Event.objects.create(
            organizer=organizer,
            name='30C3',
            slug='30c3',
            date_from=datetime.datetime(2013, 12, 26, tzinfo=datetime.UTC),
        )
        user = User.objects.create_user('test@example.com', 'test')
    with scope(organizer=event.organizer, event=event):
        v1 = event.vouchers.create(comment='Reserved for speaker', code='TEST1')
        v2 = event.vouchers.create(comment='', code='TEST2')
    return event, user, v1, v2


@pytest.mark.django_db
def test_vouchers_send_preserves_existing_comment(env):
    event, user, v1, v2 = env
    with scope(organizer=event.organizer, event=event):
        vouchers_send(
            event=event,
            vouchers=[v1.pk],
            subject='Your voucher',
            message='Here is your voucher: {voucher_list}',
            recipients=[{'email': 'speaker@example.com', 'number': 1}],
            user=user.pk,
        )
        v1.refresh_from_db()
        assert v1.comment == 'Reserved for speaker\n\nThe voucher has been sent to speaker@example.com.'


@pytest.mark.django_db
def test_vouchers_send_sets_comment_when_empty(env):
    event, user, v1, v2 = env
    with scope(organizer=event.organizer, event=event):
        vouchers_send(
            event=event,
            vouchers=[v2.pk],
            subject='Your voucher',
            message='Here is your voucher: {voucher_list}',
            recipients=[{'email': 'attendee@example.com', 'number': 1}],
            user=user.pk,
        )
        v2.refresh_from_db()
        assert v2.comment == 'The voucher has been sent to attendee@example.com.'


@pytest.mark.django_db
def test_vouchers_send_atomic_update_prevents_stale_comment_overwrite(env):
    event, user, v1, v2 = env
    with scope(organizer=event.organizer, event=event):
        v3 = event.vouchers.create(comment='Original comment', code='TEST3')

        def simulate_concurrent_edit(*args, **kwargs):
            # Staff member edits voucher comment after vouchers_send has loaded it into memory,
            # but before the database update executes
            with scope(organizer=event.organizer, event=event):
                Voucher.objects.filter(pk=v3.pk).update(comment='Staff note updated concurrently')

        with patch('eventyay.base.services.vouchers.mail', side_effect=simulate_concurrent_edit):
            vouchers_send(
                event=event,
                vouchers=[v3.pk],
                subject='Your voucher',
                message='Here is your voucher: {voucher_list}',
                recipients=[{'email': 'concurrent@example.com', 'number': 1}],
                user=user.pk,
            )

        v3.refresh_from_db()
        assert v3.comment == 'Staff note updated concurrently\n\nThe voucher has been sent to concurrent@example.com.'


@pytest.mark.django_db
def test_vouchers_send_bulk_prevents_stale_comment_overwrite(env):
    event, user, v1, v2 = env
    with scope(organizer=event.organizer, event=event):
        v3 = event.vouchers.create(comment='Original comment 1', code='BULK1')
        v4 = event.vouchers.create(comment='Original comment 2', code='BULK2')

        def simulate_concurrent_edit(*args, **kwargs):
            # Staff member edits voucher comments after vouchers_send has loaded them into memory,
            # but before the database update executes
            with scope(organizer=event.organizer, event=event):
                Voucher.objects.filter(pk=v3.pk).update(comment='Staff note updated concurrently 1')
                Voucher.objects.filter(pk=v4.pk).update(comment='Staff note updated concurrently 2')

        with patch('eventyay.base.services.vouchers.mail', side_effect=simulate_concurrent_edit):
            vouchers_send(
                event=event,
                vouchers=[v3.pk, v4.pk],
                subject='Your voucher',
                message='Here is your voucher: {voucher_list}',
                recipients=[
                    {'email': 'recipient1@example.com', 'number': 1},
                    {'email': 'recipient2@example.com', 'number': 1},
                ],
                user=user.pk,
            )

        v3.refresh_from_db()
        v4.refresh_from_db()
        # vouchers_send orders by id and pops vouchers for each recipient:
        # recipient1 gets v4 (popped first), recipient2 gets v3 (popped second)
        assert v4.comment == 'Staff note updated concurrently 2\n\nThe voucher has been sent to recipient1@example.com.'
        assert v3.comment == 'Staff note updated concurrently 1\n\nThe voucher has been sent to recipient2@example.com.'
