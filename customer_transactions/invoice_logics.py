from sqlalchemy import select, update
from database_models.pydantic_models import Invoices
from database_models.alchemy_models import Gate, GateType, Invoice, Reserved, InvoiceItem
from sqlalchemy import func
from customer_gate import entry_gate
from datetime import datetime
from prizes_logic import prize_balance_receipt_use, prize_balance_receipt_charge, earn_scores
from redis.asyncio import Redis

async def get_reserve_pre_paid_price(reserve_id, session):
    reserved_query = await session.execute(
        select(Reserved).where(Reserved.id == reserve_id)
    )
    sql_reserved = reserved_query.scalar_one_or_none()
    if sql_reserved is None:
        return 0
    else:
        return sql_reserved.pre_paid_price

async def create_invoice(customer_phone_number, session, salon_id, redis, reserve_id=None, artist_id=None, gate_id=None):
    try:
        invoice_query = await session.execute(
            select(Invoice).where(Invoice.gate_id == gate_id)
        )
        sql_invoice = invoice_query.scalar_one_or_none()
        if not sql_invoice or not gate_id:
            gate_id = await entry_gate(customer_phone_number, salon_id, session, reserve_id)
        pre_paid_price = await get_reserve_pre_paid_price(reserve_id, session)
        sql_invoice = Invoice(
            phone_number=customer_phone_number,
            created_at=datetime.now(),
            salon_id=salon_id,
            pre_paid_amount=pre_paid_price if pre_paid_price else 0,
            gate_id=gate_id,
            reserved_id=reserve_id if reserve_id else None)

        session.add_all([sql_invoice])
        await session.flush()
        # redis_invoice = Invoices(
        #     id=sql_invoice.id,
        #     created_at=sql_invoice.created_at,
        #     phone_number=customer_phone_number,
        #     status=sql_invoice.status,
        #     pre_paid_amount=sql_invoice.pre_paid_amount,
        #     gate_id=sql_invoice.gate_id,
        #     salon_id=salon_id,
        # )
        # await redis.json().set(f"models.Invoices:{sql_invoice.id}", "$", redis_invoice.dict())
        await session.commit()
        return sql_invoice.id
    except Exception as e:
        print(e)

async def service_add_to_invoice(sql_invoice_id, price, session, redis, service_id, quantity=1):
    invoice_addition = InvoiceItem(
        invoice_id=sql_invoice_id,
        service_price=price,
        is_service=True,
        quantity=quantity,
        service_id=service_id,
    )
    redis_invoice_items = await redis.json().get(f"models.Invoices:{sql_invoice_id}")
    if not redis_invoice_items:
        redis_invoice_items = {"items": {}}
    if "service" not in redis_invoice_items["items"]:
        redis_invoice_items["items"]["service"] = {}
    redis_invoice_items["items"]["service"][service_id] = {
        "invoice_id": invoice_addition.invoice_id,
        "service_price": invoice_addition.service_price,
        "quantity": invoice_addition.quantity,
    }
    await redis.json().set(f"models.Invoices:{sql_invoice_id}", "$.items", redis_invoice_items["items"])
    session.add(invoice_addition)
    await update_invoice_total_amount(session, redis, sql_invoice_id)

async def product_add_to_invoice(sql_invoice_id, price, session, redis, quantity=1):
    invoice_addition = InvoiceItem(
        invoice_id=sql_invoice_id,
        price_per_unit=price,
        is_service=False,
        quantity=quantity,
    )
    session.add(invoice_addition)
    await update_invoice_total_amount(session, redis, sql_invoice_id)

async def update_invoice_total_amount(session, redis, invoice_id):
    items_query = await session.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
    )
    items = items_query.scalars().all()
    total_price = 0
    for item in items:
        if item.is_service:
            total_price += item.service_price
        else:
            total_price += item.quantity * item.price_per_unit
    invoice_query = await session.execute(
        select(Invoice).where(Invoice.id == invoice_id)
    )
    invoice = invoice_query.scalar_one_or_none()
    if invoice:
        total_amount = total_price - invoice.pre_paid_amount
        invoice.total_amount = total_amount
    redis_invoice_items = await redis.json().get(f"models.Invoices:{invoice_id}")
    if not redis_invoice_items:
        redis_invoice_items = {"items": {}}
    redis_invoice_items["items"]["total_amount"] = total_amount
    await redis.json().set(f"models.Invoices:{invoice_id}", "$.items", redis_invoice_items["items"])

async def invoice_finalizing(session, redis, invoice_id, customer_phone_number, prize_wallet_usage=True):
    invoice_query = await session.execute(
        select(Invoice).where(Invoice.id == invoice_id)
    )
    invoice = invoice_query.scalar_one_or_none()
    if prize_wallet_usage:
        paid_price = await prize_balance_receipt_use(invoice.total_amount, customer_phone_number, invoice.salon_id, session, redis, invoice_id)
    else:
        paid_price = invoice.total_amount
    await prize_balance_receipt_charge(customer_phone_number, invoice.salon_id, invoice.total_amount, session, redis, invoice_id)
    await earn_scores(customer_phone_number, paid_price, session, redis)

async def main():
    from database_models.databases_connections import get_async_session, redis
    async with get_async_session() as session:
        customer_phone_number = "09011401001"
        salon_id = 1
        try:
            invoice_id = await create_invoice(customer_phone_number, session, salon_id, redis)
            print(f"Invoice created successfully with ID: {invoice_id}")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())