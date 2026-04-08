import pytest
from unittest.mock import patch, MagicMock
from lib import models

class TestTransactionModel:
    def test_valid_transaction(self):
        data = {
            'id': '1',
            'legId': 'leg1',
            'type': 'CARD_PAYMENT',
            'state': 'COMPLETED',
            'startedDate': 1672531200000, # 2023-01-01 00:00:00 UTC
            'updatedDate': 1672531200000,
            'completedDate': 1672531200000,
            'createdDate': 1672531200000,
            'currency': 'EUR',
            'amount': 10.0,
            'tag': 'general',
            'category': 'groceries',
            'account': {'id': 'acc1'},
            'merchant': {'category': 'supermarket', 'name': 'Tesco'}
        }
        model = models.TransactionModel(**data)
        assert model.amount == 10.0
        
        # The code uses datetime.fromtimestamp() which uses system local time.
        # We must expect the same.
        from datetime import datetime
        expected_dt = datetime.fromtimestamp(1672531200000 / 1000)
        # Pydantic parses the isoformat string back to a naive datetime (usually)
        # The result in failure was datetime(2023, 1, 1, 1, 0)
        
        # We need to strip microseconds if the original code's isoformat() loop does something? 
        # No, isoformat keeps them. But 0 microseconds are often dropped in string repr but kept in object.
        # Let's just compare.
        assert model.startedDate == expected_dt
        assert model.merchant_name == 'Tesco'

    def test_custom_category_mapping(self):
        uuid_like = '11111111-2222-3333-4444-555555555555'
        data = {
            'id': '1',
            'legId': 'leg1',
            'type': 'CARD_PAYMENT',
            'state': 'COMPLETED',
            'startedDate': 1672531200000,
            'currency': 'EUR',
            'amount': 10.0,
            'tag': 'general',
            'category': uuid_like,
            'account': {'id': 'acc1'}
        }
        
        with patch.dict(models.custom_categories_map, {uuid_like: 'MyCategory'}):
             model = models.TransactionModel(**data)
             assert model.category == 'MyCategory'

    def test_missing_custom_category_raises(self):
         uuid_like = '11111111-2222-3333-4444-555555555555'
         data = {
            'id': '1',
            'legId': 'leg1',
            'type': 'CARD_PAYMENT',
            'state': 'COMPLETED',
            'startedDate': 1672531200000,
            'currency': 'EUR',
            'amount': 10.0,
            'tag': 'general',
            'category': uuid_like,
            'account': {'id': 'acc1'}
        }
         # Ensure it's not in the map
         with patch.dict(models.custom_categories_map, {}, clear=True):
             with pytest.raises(Exception) as exc:
                 models.TransactionModel(**data)
             assert f'Category with ID {uuid_like} was not found' in str(exc.value)

    def test_date_conversion_none(self, caplog):
        # Test when date is None/0
        data = {
            'id': '1',
            'legId': 'leg1',
            'type': 'CARD_PAYMENT',
            'state': 'COMPLETED',
            'currency': 'EUR',
            'amount': 10.0,
            'tag': 'general',
            'category': 'cat',
            'account': {'id': 'acc1'},
            'startedDate': 0
        }
        with caplog.at_level('ERROR'):
            model = models.TransactionModel(**data)
            assert model.startedDate is None
            assert 'Cannot convert 0 to datetime obj' in caplog.text

    def test_non_uuid_category(self):
        data = {
            'id': '1',
            'legId': 'leg1',
            'type': 'CARD_PAYMENT',
            'state': 'COMPLETED',
            'currency': 'EUR',
            'amount': 10.0,
            'tag': 'general',
            'category': 'normal-category',
            'account': {'id': 'acc1'}
        }
        model = models.TransactionModel(**data)
        assert model.category == 'normal-category'
