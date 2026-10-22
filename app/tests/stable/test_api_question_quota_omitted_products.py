import pytest
from django_scopes import scope, scopes_disabled
from rest_framework.test import APIClient

from eventyay.base.models import Product, ProductVariation, Question, Quota, SubEvent


@pytest.fixture
@scopes_disabled()
def token_client(team):
    """Return an API client authenticated with an organizer team token."""
    client = APIClient()
    token = team.tokens.create(name='TestToken')
    client.credentials(HTTP_AUTHORIZATION='Token ' + token.token)
    return client


@pytest.mark.django_db
def test_question_create_omitted_products(token_client, organizer, event):
    """Omitting optional products field creates question with 201 Created and empty products."""
    resp = token_client.post(
        f'/api/v1/organizers/{organizer.slug}/events/{event.slug}/questions/',
        {
            'question': 'Your name?',
            'type': 'S',
            'required': False,
            'identifier': None,
        },
        format='json',
    )
    assert resp.status_code == 201
    with scopes_disabled():
        question = Question.objects.get(pk=resp.data['id'])
        assert question.question == 'Your name?'
        assert question.products.count() == 0


@pytest.mark.django_db
def test_quota_create_omitted_products_and_variations(token_client, organizer, event):
    """Omitting products and variations fields creates quota with 201 Created."""
    resp = token_client.post(
        f'/api/v1/organizers/{organizer.slug}/events/{event.slug}/quotas/',
        {
            'name': 'Main quota',
            'size': 10,
        },
        format='json',
    )
    assert resp.status_code == 201
    with scopes_disabled():
        quota = Quota.objects.get(pk=resp.data['id'])
        assert quota.name == 'Main quota'
        assert quota.size == 10
        assert quota.products.count() == 0
        assert quota.variations.count() == 0


@pytest.mark.django_db
def test_quota_create_variations_without_products_returns_400(token_client, organizer, event):
    """Sending variations without products returns 400 Bad Request instead of 500 TypeError."""
    with scope(organizer=organizer, event=event):
        prod = Product.objects.create(event=event, name='Ticket', default_price=10)
        var = ProductVariation.objects.create(product=prod, value='Standard')

    resp = token_client.post(
        f'/api/v1/organizers/{organizer.slug}/events/{event.slug}/quotas/',
        {
            'name': 'Quota with variation only',
            'size': 10,
            'variations': [var.pk],
        },
        format='json',
    )
    assert resp.status_code == 400
    assert 'All variations must belong to an product contained in the products list.' in str(resp.data)


@pytest.mark.django_db
def test_quota_create_product_with_variations_omitted_variations_returns_400(token_client, organizer, event):
    """Sending product with variations but omitting variations returns 400 Bad Request instead of 500."""
    with scope(organizer=organizer, event=event):
        prod = Product.objects.create(event=event, name='Ticket with variations', default_price=10)
        ProductVariation.objects.create(product=prod, value='VIP')

    resp = token_client.post(
        f'/api/v1/organizers/{organizer.slug}/events/{event.slug}/quotas/',
        {
            'name': 'Quota without variations',
            'size': 10,
            'products': [prod.pk],
        },
        format='json',
    )
    assert resp.status_code == 400
    assert 'One or more products has variations but none of these are in the variations list.' in str(resp.data)


@pytest.mark.django_db
def test_clean_products_and_variations_helpers_none_safe(event):
    """clean_products and clean_variations model methods safely handle None inputs without TypeError."""
    with scope(organizer=event.organizer, event=event):
        # Should not raise TypeError: 'NoneType' object is not iterable
        Question.clean_products(event, None)
        Quota.clean_variations(None, None)
        Quota.clean_products(event, None, None)
        SubEvent.clean_products(event, None)
        SubEvent.clean_variations(event, None)
