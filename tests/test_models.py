import pytest
from lib.models import TransactionModel
from datetime import datetime
import lib.models

def test_transaction_model_valid(mocker):
    # Use a proper UUID-like string with 4 dashes (5 parts)
    uuid = '11111111-2222-3333-4444-555555555555'
    mocker.patch.dict('lib.models.custom_categories_map', {uuid: 'Food'}, clear=True)
    
    data = {
        'id': '1',
        'legId': 'leg1',
        'type': 'CARD_PAYMENT',
        'state': 'COMPLETED',
        'startedDate': 1704067199000,
        'currency': 'EUR',
        'amount': -10.5,
        'tag': 'tag1',
        'category': uuid,
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

def test_transaction_model_invalid_category(mocker):
    uuid = '00000000-0000-0000-0000-000000000000'
    mocker.patch.dict('lib.models.custom_categories_map', {}, clear=True)
    
    data = {
        'id': '1',
        'legId': 'leg1',
        'type': 'CARD_PAYMENT',
        'state': 'COMPLETED',
        'startedDate': 1704067199000,
        'currency': 'EUR',
        'amount': -10.5,
        'tag': 'tag1',
        'category': uuid,
        'account': {'id': 'acc1'}
    }
    
    with pytest.raises(Exception) as excinfo:
        TransactionModel(**data)
    assert 'was not found' in str(excinfo.value)

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
