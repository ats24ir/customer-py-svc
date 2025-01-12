from sqlalchemy import  select, update
from database_models.alchemy_models import Gate, GateType, Invoice,Reserved,InvoiceItem
from sqlalchemy import  select,func
from customer_gate import entry_gate
from datetime import datetime
from prizes_logic import prize_balance_receipt_use,prize_balance_receipt_charge,earn_scores

def get_reserve_pre_paid_price(reserve_id,session):
    reserved_query = session.execute(
        select(Reserved).where(Reserved.id == reserve_id)
    )
    sql_reserved = reserved_query.scalar_one_or_none()
    if sql_reserved is None:
        return 0
    else:
        return sql_reserved.pre_paid_price

def create_invoice(gate_id,customer_phone_number,session,salon_id,reserve_id=None,artist_id=None):
        try:
            invoice_query = session.execute(
                select(Invoice).where(Invoice.gate_id == gate_id)
            )
            sql_invoice = invoice_query.scalar_one_or_none()
            if not sql_invoice:
                new_gate=entry_gate(customer_phone_number,reserve_id)
                pre_paid_price=get_reserve_pre_paid_price(reserve_id,session)
                sql_invoice = Invoice(
                phone_number=customer_phone_number,
                    created_at=datetime.now(),
                    salon_id=salon_id,
                    pre_paid_amount=pre_paid_price if pre_paid_price else 0,
                    gate_id=reserve_id if reserve_id else None)
                session.add_all([new_gate,sql_invoice])
            return sql_invoice.id
        except Exception as e:
            print(e)

def service_add_to_invoice(sql_invoice_id,price,session,quantity=1):
    invoice_addition = InvoiceItem(
        invoice_id = sql_invoice_id,
        service_price=price,
        is_service=True,
        quantity=quantity,
    )
    session.add(invoice_addition)
    update_invoice_total_amount(session,sql_invoice_id)

def product_add_to_invoice(sql_invoice_id,price,session,quantity=1):
    invoice_addition = InvoiceItem(
        invoice_id = sql_invoice_id,
        price_per_unit=price,
        is_service=False,
        quantity=quantity,
    )
    session.add(invoice_addition)
    update_invoice_total_amount(session,sql_invoice_id)

def update_invoice_total_amount(session, invoice_id):
    items = session.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()
    total_price = 0
    for item in items:
        if item.is_service:
            total_price += item.service_price
        else:
            total_price += item.quantity * item.price_per_unit
    invoice = session.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice:
        total_amount = total_price - invoice.pre_paid_amount
        invoice.total_amount = total_amount

def invoice_finalizing(session,invoice_id,customer_phone_number):
    invoice = session.query(Invoice).filter(Invoice.id == invoice_id).first()
    paid_price=prize_balance_receipt_use(invoice.total_amount-invoice.pre_paid_amount,customer_phone_number,invoice.salon_id,session,invoice_id)
    prize_balance_receipt_charge(customer_phone_number,invoice.salon_id,invoice.total_amount,session,invoice_id)
    earn_scores(customer_phone_number,paid_price,session)



