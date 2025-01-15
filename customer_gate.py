from database_models.alchemy_models import Gate, GateType, Invoice
from database_models.databases_connections import get_async_session, redis
from datetime import datetime
from sqlalchemy import select
from login_logic.customer_create import customer_get_or_create
from sqlalchemy.ext.asyncio import AsyncSession

async def entry_gate(phone_number: str, salon_id: int, session, operator: str = None, reserve_id: int = None) -> int:

    try:
        await customer_get_or_create(phone_number, session, redis)

        # Create a new gate entry
        new_entry = Gate(
            phone_number=phone_number,
            entered_at=datetime.now(),
            salon_id=salon_id,
            type=GateType.RESERVED if reserve_id else GateType.UNRESERVED,
            reserve_id=reserve_id if reserve_id else None,
            operator=operator if operator else "Reservation"
        )
        session.add(new_entry)
        session.flush()
        await session.commit()
        return new_entry.id
    except Exception as e:
        print(f"The error in gate: {e}")
        await session.rollback()
        raise

async def exit_gate(phone_number: str, session: AsyncSession):

    try:
        # Find the latest gate entry for the customer that hasn't exited yet
        gate_query = await session.execute(
            select(Gate)
            .where(Gate.phone_number == phone_number)
            .where(Gate.exited_at == None)
            .where(Gate.presence_status == "InSalon")
            .order_by(Gate.entered_at.desc())
        )
        sql_gate = gate_query.scalar_one_or_none()

        if not sql_gate:
            raise ValueError("You have no entry")

        # Check if the customer has a pending invoice
        if sql_gate.invoice_id:
            invoice_query = await session.execute(
                select(Invoice).where(Invoice.phone_number == phone_number)
            )
            sql_invoice = invoice_query.scalar_one_or_none()
            if sql_invoice.status == "Pending":
                raise ValueError("You have a pending invoice")

        # Update the gate entry to mark the exit
        sql_gate.exited_at = datetime.now()
        sql_gate.presence_status = "Exited"
        session.add(sql_gate)
        await session.commit()
    except Exception as e:
        print(f"The error in gate: {e}")
        await session.rollback()
        raise