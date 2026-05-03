import logging
from pydantic import BaseModel, Field, field_validator, AliasPath
from typing import Optional
from datetime import datetime
from lib.inputs import Inputs

logger = logging.getLogger('revol_ver')
custom_categories_map = Inputs.get_ini_config('custom.categories')

class TransactionModel(BaseModel):
    '''
    Represents a single Revolut transaction.
    '''
    id: str
    legId: str
    type: str
    state: str
    startedDate: Optional[datetime] = None
    updatedDate: Optional[datetime] = None
    completedDate: Optional[datetime] = None
    createdDate: Optional[datetime] = None
    currency: str
    amount: float
    fee: Optional[float] = 0.0
    balance: Optional[float] = 0.0
    amountWithCharges: Optional[float] = None
    description: Optional[str] = ''
    reason: Optional[str] = ''
    tag: str
    category: str
    relatedTransactionId: Optional[str] = ''
    account_id: Optional[str] = Field(None, validation_alias=AliasPath('account', 'id'))
    account_type: Optional[str] = Field(None, validation_alias=AliasPath('account', 'type'))
    countryCode: Optional[str] = ''
    rate: Optional[float] = None
    merchant_category: Optional[str] = Field(None, validation_alias=AliasPath('merchant', 'category'))
    merchant_name: Optional[str] = Field(None, validation_alias=AliasPath('merchant', 'name'))
    merchant_mcc: Optional[str] = Field(None, validation_alias=AliasPath('merchant', 'mcc'))
    merchant_scheme: Optional[str] = Field(None, validation_alias=AliasPath('merchant', 'scheme'))
    merchant_city: Optional[str] = Field(None, validation_alias=AliasPath('merchant', 'city'))
    merchant_country: Optional[str] = Field(None, validation_alias=AliasPath('merchant', 'country'))
    merchant_state: Optional[str] = Field(None, validation_alias=AliasPath('merchant', 'state'))
    merchant_postcode: Optional[str] = Field(None, validation_alias=AliasPath('merchant', 'postcode'))
    merchant_address: Optional[str] = Field(None, validation_alias=AliasPath('merchant', 'address'))
    counterpart_amount: Optional[float] = Field(None, validation_alias=AliasPath('counterpart', 'amount'))
    counterpart_currency: Optional[str] = Field(None, validation_alias=AliasPath('counterpart', 'currency'))
    comment: Optional[str] = ''
    cardLastFour: Optional[str] = ""
    cardLabel: Optional[str] = ""

    @field_validator('startedDate', 'updatedDate', 'completedDate', 'createdDate', mode='before')
    def convert_started_date(cls, epoch: int) -> datetime:
        if epoch:
            # Convert milliseconds to seconds and then to ISO format
            dt = datetime.fromtimestamp(epoch / 1000).isoformat()
            #logger.debug(f'Converted {epoch} to datetime obj {dt}')
            return dt
        logger.error(f'Cannot convert {epoch} to datetime obj')

    @field_validator('category', mode='before')
    def id_to_custom_category(cls, cat: str, trans: dict) -> str:
        'Translates custom category UUID to category defined in config.ini'
        if len(cat.split('-')) != 5:   # detects uuid
            return cat
        pretty_cat = custom_categories_map.get(cat)
        if not pretty_cat:
            raise Exception(f'\nCategory with ID {cat} was not found. Full transaction:\n{str(trans)}')
        logger.debug(f'Resolved category ID {cat} to {pretty_cat}')
        return pretty_cat
