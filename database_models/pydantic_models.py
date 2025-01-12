from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class InvoiceStatus(Enum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PENDING = "pending"

class ServicesOptions(BaseModel):
    name: str = Field(...)
    price: int = Field(...)

class Receipts(BaseModel):
    id: str = Field(...)
    amount: int = Field(...)
    wallet_id: str = Field(...)
    created_at: str = Field(...)
    is_spent: bool = Field(...)
    phone_number: str = Field(...)

class Invoices(BaseModel):
    id: str = Field(...)
    total_amount: int = Field(...)
    created_at: str = Field(...)
    services_id: list = Field(...)
    phone_number: str = Field(...)
    status: str

class Services(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    price: int = Field(...)
    duration: int = Field(...)
    options: Optional[List[ServicesOptions]] = Field(None)


class Artists(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    age: int = Field(...)
    city: str = Field(...)
    services: List[Services] = Field(...)
    working_hours: Dict = Field(...)

class Wallets(BaseModel):
    id: str = Field(...)
    in_to_wallet: int = Field(...)
    out_of_wallet: int = Field(...)
    customer_id: int = Field(...)


class SalonPrizeWallet(BaseModel):
    id: str = Field(...)
    in_to_prize_balance: int = Field(...)
    out_of_prize_balance: int = Field(...)
    in_to_timed_prize_balance: int = Field(...)
    out_of_timed_prize_balance: int = Field(...)
    salon_id: str = Field(...)
    customer_id: str = Field(...)


class SalonPrizeWalletReceipts(BaseModel):
    id: str = Field(...)
    is_spent: bool = Field(...)
    timed_amount: int = Field(...)
    unlimited_amount: int = Field(...)
    created_at: str = Field(...)
    customer_id: str = Field(...)
    salon_id: str = Field(...)


class ScoresWallets(BaseModel):
    id: str = Field(...)
    in_to_scores_wallet: int = Field(0)
    out_of_scores_balance: int = Field(0)
    customer_id: str = Field(...)

class ScoresWalletReceipt(BaseModel):
    id: str = Field(...)
    is_spent: bool = Field(...)
    amount:int= Field(...)
    created_at: datetime = Field(...)
    customer_id: str = Field(...)


class CustomerGroups(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    pay_free_reserve: bool = Field(False)
    to_prize_wallet_percentage: int = Field(0)
    to_timed_prize_wallet_percentage: int = Field(0)
    prize_wallet_usage_ratio: int = Field(0)
    salon_id: str = Field(...)
    points_needed:int = Field(0)


class Customers(BaseModel):
    id: str = Field(...)
    name: Optional[str] = Field(None)
    age: Optional[int] = Field(None)
    city: Optional[str] = Field(None)
    phone_number: str = Field(...)
    birthday: Optional[str] = Field(None)
    marriage_anniversary: Optional[str] = Field(None)
    special_days: Optional[List[str]] = Field(None)
    secondary_phone_number: Optional[str] = Field(None)


class Salons(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    age: int = Field(...)
    city: str = Field(...)
    artists: List[Artists] = Field(...)
    services: List[Services] = Field(...)


class Reserve(BaseModel):
    id: int
    time: str = Field(None)
    time_jalali: str = Field(None)
    start_stamp: int
    end_stamp: int

    available: bool = Field
    salon_id: int = Field(...)
    salon_name: str = Field(...)
    artist_id: int = Field(...)
    artist_name: str = Field(...)
    service_id: int = Field(...)
    service_name: str = Field(...)

    phone_number: str = Field(...)
    reserved_at_datetime: Optional[str] = Field(None)
    reserved_at_timestamp: Optional[int] = Field(None)
    reserved_at_jalali: Optional[str] = Field(None)
    reserved_at: Optional[str] = Field(None)


class CanceledReservations(BaseModel):
    time: str = Field(...)
    salon: str = Field(...)
    artist: str = Field(...)
    service: Services = Field(...)
    customer: Customers = Field(...)
    cancellation_time: datetime = Field(...)



