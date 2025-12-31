import logging
from pydantic import BaseModel, Field, field_validator, AliasPath
from typing import Optional
from datetime import datetime

logger = logging.getLogger('revol_ver')

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
    description: Optional[str] = ''
    tag: str
    category: str
    relatedTransactionId: Optional[str] = ''
    account_id: Optional[str] = Field(None, validation_alias=AliasPath('account', 'id'))
    countryCode: Optional[str] = ''
    rate: Optional[float] = None
    merchant_category: Optional[str] = Field(None, validation_alias=AliasPath('merchant', 'category'))
    merchant_name: Optional[str] = Field(None, validation_alias=AliasPath('merchant', 'name'))
    comment: Optional[str] = ''

    @field_validator('startedDate', 'updatedDate', 'completedDate', 'createdDate', mode='before')
    def convert_started_date(cls, epoch: int) -> datetime:
        if epoch:
            # Convert milliseconds to seconds and then to ISO format
            dt = datetime.fromtimestamp(epoch / 1000).isoformat()
            #logger.debug(f'Converted {epoch} to datetime obj {dt}')
            return dt
        logger.error(f'Cannot convert {epoch} to datetime obj')

class AuthData(BaseModel):
    cookie: str
    device_id: str
    pocket_id: str = ''
    wallet_id: str = ''
    account_type: str = ''