import pytest
from lib.models import TransactionModel
from datetime import datetime
import lib.models
from revol_ver import id_to_custom_category

def test_transaction_model_valid(mocker):
    # Use a proper UUID-like string with 4 dashes (5 parts)
    uuid = '11111111-2222-3333-4444-555555555555'
    #mocker.patch.dict('inputs.custom_categories_map', {uuid: 'Food'}, clear=True)
    pretty_cat = id_to_custom_category({uuid: 'Food'}, uuid)
    data = {
        'id': '1',
        'legId': 'leg1',
        'type': 'CARD_PAYMENT',
        'state': 'COMPLETED',
        'startedDate': 1704067199000,
        'currency': 'EUR',
        'amount': -10.5,
        'tag': 'tag1',
        'category': pretty_cat,
        'account': {'id': 'acc1'},
        'merchant': {'category': 'groceries', 'name': 'Lidl'}
    }
    
    model = TransactionModel(**data)
    assert model.id == '1'
    assert model.amount == -10.5
    assert model.category == 'Food'
    assert isinstance(model.startedDate, datetime)
    assert model.account_id == 'acc1'
    assert model.merchant_category == 'groceries'


def test_transaction_model_regular_category():
    data = {
        'id': '1',
        'legId': 'leg1',
        'type': 'CARD_PAYMENT',
        'state': 'COMPLETED',
        'startedDate': 1704067199000,
        'currency': 'EUR',
        'amount': -10.5,
        'tag': 'tag1',
        'category': 'general',
        'account': {'id': 'acc1'}
    }
    model = TransactionModel(**data)
    assert model.category == 'general'

def test_convert_started_date_none(mocker):
    import logging
    logger = logging.getLogger('revol_ver')
    mock_error = mocker.patch.object(logger, 'error')
    
    data = {
        'id': '1', 'legId': 'l1', 'type': 't', 'state': 's', 'currency': 'EUR', 'amount': 0, 'tag': 't', 'category': 'c',
        'startedDate': None
    }
    model = TransactionModel(**data)
    assert model.startedDate is None
    mock_error.assert_called_with('Cannot convert None to datetime obj')
