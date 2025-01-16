from curses.textpad import Textbox

from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, UniqueConstraint, Table, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from enum import Enum as PyEnum
from sqlalchemy.ext.hybrid import hybrid_property
from urllib.parse import quote
import psycopg2  # For database creation

# Define enums
class InvoiceStatus(PyEnum):
    COMPLETED = "Completed"
    PENDING = "Pending"
    CANCELLED = "Cancelled"

class GateType(PyEnum):
    RESERVED = "Reserved"
    UNRESERVED = "Unreserved"

class PresenceStatus(PyEnum):
    INSALON = "InSalon"
    EXITED = "Exited"
    UNPAID = "UnPaid"

# Base for SQLAlchemy models
Base = declarative_base()

# Association tables
salon_artist = Table('salon_artist', Base.metadata,
                     Column('salon_id', Integer, ForeignKey('salon.id')),
                     Column('artist_id', Integer, ForeignKey('artist.id'))
                     )

salon_service = Table('salon_service', Base.metadata,
                      Column('salon_id', Integer, ForeignKey('salon.id')),
                      Column('service_id', Integer, ForeignKey('service.id'))
                      )

artist_service = Table('artist_service', Base.metadata,
                       Column('artist_id', Integer, ForeignKey('artist.id')),
                       Column('service_id', Integer, ForeignKey('service.id'))
                       )

# Define models (unchanged)
class IncomePrizes(Base):
    __tablename__ = 'income_prizes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String, ForeignKey('customer.phone_number'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    amount = Column(Integer, nullable=False)
    salon_id = Column(Integer, ForeignKey('salon.id'), nullable=True)
    expire_date = Column(DateTime, nullable=True)
    awarded_for_invoice_id = Column(Integer, ForeignKey('invoice.id'), nullable=True)
    remaining_amount = Column(Integer, nullable=False)

class OutcomePrize(Base):
    __tablename__ = 'outcome'
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String, ForeignKey('customer.phone_number'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    amount = Column(Integer, nullable=False)
    salon_id = Column(Integer, ForeignKey('salon.id'), nullable=False)
    invoice_spent_on = Column(Integer, ForeignKey('invoice.id'), nullable=False)
    income_id = Column(Integer, ForeignKey('income_prizes.id'), nullable=False)

class PrizeWallets(Base):
    __tablename__ = 'prizewallets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_phone_number = Column(String, ForeignKey('customer.phone_number'), nullable=False)
    salon_id = Column(Integer, ForeignKey('salon.id'), nullable=True)
    balance = Column(Integer, nullable=False)

class Salon(Base):
    __tablename__ = 'salon'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    city = Column(String, nullable=False)

    artists = relationship("Artist", secondary=salon_artist, back_populates="salons")
    services = relationship("Service", secondary=salon_service, back_populates="salons")
    salon_customer_groups = relationship("SalonCustomerGroup", back_populates="salon")

class CustomerGroup(Base):
    __tablename__ = 'customer_group'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    to_prize_balance_percentage = Column(Integer, nullable=True)
    cashback_expire_in_days = Column(Integer, nullable=True, default=30)
    prize_wallet_usage_ratio = Column(Integer, nullable=True)
    pre_pay_percentage = Column(Integer, nullable=False)
    points_needed = Column(Integer, default=0, nullable=False)

    salon_customer_groups = relationship("SalonCustomerGroup", back_populates="group")

class SalonCustomerGroup(Base):
    __tablename__ = 'salon_customer_group'
    id = Column(Integer, primary_key=True, autoincrement=True)
    salon_id = Column(Integer, ForeignKey('salon.id'), nullable=False)
    group_id = Column(Integer, ForeignKey('customer_group.id'), nullable=False)
    __table_args__ = (UniqueConstraint('salon_id', 'group_id', name='salon_group_unique'),)

    salon = relationship("Salon", back_populates="salon_customer_groups")
    group = relationship("CustomerGroup", back_populates="salon_customer_groups")

class ServiceOption(Base):
    __tablename__ = 'service_option'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    service_id = Column(Integer, ForeignKey('service.id'), nullable=False)

    service = relationship("Service", back_populates="options")

class Service(Base):
    __tablename__ = 'service'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)
    descriptions = Column (String , nullable=True )
    options = relationship("ServiceOption", back_populates="service")
    artists = relationship("Artist", secondary=artist_service, back_populates="services")
    salons = relationship("Salon", secondary=salon_service, back_populates="services")

class Artist(Base):
    __tablename__ = 'artist'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    city = Column(String, nullable=False)
    working_hours = Column(JSON, nullable=False)

    services = relationship("Service", secondary=artist_service, back_populates="artists")
    salons = relationship("Salon", secondary=salon_artist, back_populates="artists")

class Customer(Base):
    __tablename__ = 'customer'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    city = Column(String, nullable=True)
    phone_number = Column(String, unique=True, nullable=False)
    birthday = Column(String, nullable=True)
    marriage_anniversary = Column(String, nullable=True)
    special_days = Column(String, nullable=True)
    secondary_phone_number = Column(String, unique=True, nullable=True)

    scores_receipts = relationship("ScoresReceipt", back_populates="related_customer")
    wallet = relationship("Wallet", uselist=False, back_populates="customer", foreign_keys="Wallet.customer_id")
    invoices = relationship("Invoice", back_populates="customer")
    scores_wallets = relationship("ScoresWallet", back_populates="related_customer")

class ScoresWallet(Base):
    __tablename__ = 'scores_wallet'
    id = Column(Integer, primary_key=True, autoincrement=True)
    in_to_scores_wallet = Column(Integer, default=0)
    out_of_scores_wallet = Column(Integer, default=0)
    phone_number = Column(String, ForeignKey('customer.phone_number'), nullable=False)

    related_customer = relationship("Customer", back_populates="scores_wallets")

class ScoresReceipt(Base):
    __tablename__ = 'scores_receipt'
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String, ForeignKey('customer.phone_number'), nullable=False)
    created_at = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    is_spent = Column(Boolean, nullable=False)

    related_customer = relationship("Customer", back_populates="scores_receipts")

class Receipts(Base):
    __tablename__ = 'receipts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Integer, nullable=False)
    created_at = Column(String, nullable=False)
    is_spent = Column(Boolean, nullable=False)
    phone_number = Column(String, ForeignKey('customer.phone_number'), nullable=False)
    wallet_id = Column(Integer, ForeignKey('wallet.id'), nullable=False)
    wallet = relationship("Wallet", back_populates="receipts")
    invoice_id = Column(Integer, ForeignKey('invoice.id'), nullable=True)
    reserve_id = Column(Integer, ForeignKey('reserved.id'), nullable=True)
    invoice = relationship("Invoice", back_populates="receipt", uselist=False)

class Invoice(Base):
    __tablename__ = 'invoice'
    id = Column(Integer, primary_key=True, autoincrement=True)
    total_amount = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)
    phone_number = Column(String, ForeignKey('customer.phone_number'), nullable=False)
    status = Column(Enum(InvoiceStatus, name="invoice_status_enum"), nullable=False, default=InvoiceStatus.PENDING)
    pre_paid_amount = Column(Integer, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    gate_id = Column(Integer, ForeignKey('gate.id'), nullable=False)
    reserved_id = Column(Integer, ForeignKey('reserved.id'), nullable=True)
    salon_id = Column(Integer, ForeignKey('salon.id'), nullable=False)
    customer = relationship("Customer", back_populates="invoices")
    receipt = relationship("Receipts", back_populates="invoice", uselist=False)
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceItem(Base):
    __tablename__ = 'invoice_item'
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey('invoice.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_per_unit = Column(Integer, nullable=True)
    service_price = Column(Integer, nullable=True)
    is_service = Column(Boolean, nullable=False)
    service_id = Column(Integer, ForeignKey('service.id'), nullable=True)
    #product_id=Column(Integer,ForeignKey('service.id'), nullable=True)
    invoice = relationship("Invoice", back_populates="items")

class Gate(Base):
    __tablename__ = 'gate'
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String, nullable=False)
    entered_at = Column(DateTime, nullable=False)
    salon_id = Column(Integer, ForeignKey('salon.id'), nullable=False)
    exited_at = Column(DateTime, nullable=True)
    presence_status = Column(Enum(PresenceStatus, name="Presence_status_enum"), default=PresenceStatus.INSALON)
    reserve_id = Column(Integer, ForeignKey('reserved.id'), nullable=True)
    invoice_id = Column(Integer, ForeignKey('invoice.id'), nullable=True)
    invoice_closed_at = Column(DateTime, nullable=True)
    type = Column(Enum(GateType, name="gate_type_enum"), nullable=True)
    operator = Column(String, default="Reservation")

class Wallet(Base):
    __tablename__ = 'wallet'
    id = Column(Integer, primary_key=True, autoincrement=True)
    in_to_wallet = Column(Integer, default=0)
    out_of_wallet = Column(Integer, default=0)
    phone_number = Column(String, ForeignKey('customer.phone_number'), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey('customer.id'), unique=True, nullable=False)
    customer = relationship("Customer", back_populates="wallet", foreign_keys=[customer_id])
    receipts = relationship("Receipts", back_populates="wallet")

    @hybrid_property
    def balance(self):
        return self.in_to_wallet - self.out_of_wallet

    @balance.expression
    def balance(cls):
        return cls.in_to_wallet - cls.out_of_wallet

class Reserved(Base):
    __tablename__ = 'reserved'
    id = Column(Integer, primary_key=True)
    time = Column(DateTime, nullable=False)
    time_jalali = Column(DateTime, nullable=False)
    salon_id = Column(Integer, ForeignKey('salon.id'), nullable=False)
    artist_id = Column(Integer, ForeignKey('artist.id'), nullable=False)
    service_id = Column(Integer, ForeignKey('service.id'), nullable=False)
    phone_number = Column(String, ForeignKey('customer.phone_number'), nullable=True)
    pre_paid_amount = Column(Integer, nullable=False)
    reserved_at_datetime = Column(DateTime, nullable=True)
    reserved_at_timestamp = Column(Integer, nullable=True)
    reserved_at_jalali = Column(String, nullable=True)
    reserved_at = Column(String, nullable=True)

# Function to create the database if it doesn't exist
def create_database():
    try:
        # Connect to the default PostgreSQL database
        conn = psycopg2.connect(
            dbname="postgres",  # Connect to the default 'postgres' database
            user="rsvpuser",
            password="123@",
            host="localhost",
            port="5432"
        )
        conn.autocommit = True  # Enable autocommit for database creation
        cursor = conn.cursor()

        # Check if the database exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = 'rsvp'")
        exists = cursor.fetchone()

        # Create the database if it doesn't exist
        if not exists:
            cursor.execute("CREATE DATABASE rsvp")
            print("Database 'rsvp_dev' created successfully.")
        else:
            print("Database 'rsvp_dev' already exists.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")

# Create the database if it doesn't exist
# create_database()

# Create the SQLAlchemy engine for the new database
password = "123@"
encoded_password = quote(password)
engine = create_engine(f'postgresql://pyuser:{encoded_password}@localhost:5433/rsvp_dev', echo=True)
session = Session(bind=engine)

# Function to create tables
def create_tables():
    with engine.begin() as conn:
        Base.metadata.create_all(conn)
    print("Tables created successfully.")

# Main function
def main():
    create_tables()

if __name__ == "__main__":
    main()