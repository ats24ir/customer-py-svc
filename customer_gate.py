from database_models.alchemy_models import Gate, GateType, Invoice,PresenceStatus
from database_models.pydantic_models import Gate as Redis_Gate
from database_models.databases_connections import get_async_session, redis
from datetime import datetime
from sqlalchemy import select

from generate import logger
from login_logic.customer_create import customer_get_or_create

async def entry_gate(phone_number, salon_id, session,redis, artist_id = None, reserve_id = None):
    try:
        await customer_get_or_create(phone_number, session, redis)
        # Checking for Unexited Entry and Closing Them
        #Postgres Implantation
        sql_gate = await find_customer_gate(phone_number,salon_id,session)
        if sql_gate:
            for gate in sql_gate:
                gate.presence_status=PresenceStatus.SYSTEMCLOSED
                session.add(gate)
                await redis.json().set(f"models.Gate:{gate.id}","$.presence_status","SystemClosed")


        # Create a new gate entry
        #Postgres Implantation
        new_entry = Gate(
            phone_number=phone_number,
            entered_at=datetime.now(),
            salon_id=salon_id,
            type=GateType.RESERVED if reserve_id else GateType.UNRESERVED,
            reserve_id=reserve_id if reserve_id else None,
            operator=f"Artist Id {artist_id}" if artist_id else "Reservation"
        )
        session.add(new_entry)
        await session.commit()
        #Redis Implantation
        redis_gate = Redis_Gate(
            phone_number=phone_number,
            id=new_entry.id,
            entered_at=new_entry.entered_at.strftime("%Y-%m-%d %H:%M"),
            salon_id=salon_id,
            type=new_entry.type,
            reserve_id=new_entry.reserve_id,
            operator=new_entry.operator
        )
        await redis.json().set(f"models.Gate:{new_entry.id}", "$", redis_gate.dict())
        return new_entry.id
    except Exception as e:
        print(f"The error in gate: {e}")
        await session.rollback()
        raise


async def exit_gate(phone_number,salon_id, session,redis):

    try:
        # Find the latest gate entry for the customer that hasn't exited yet
        sql_gate = await find_customer_gate(phone_number,salon_id,session)

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
        await redis.json().set(f"models.Gate:{sql_gate.id}", "$.exited_at", sql_gate.exited_at.strftime("%Y-%m-%d %H:%M"))
        await redis.json().set(f"models.Gate:{sql_gate.id}", "$.presence_status", "Exited")
    except Exception as e:
        print(f"The error in gate: {e}")
        await session.rollback()
        raise


async def find_customer_gate(phone_number,salon_id, session):
    try:
        logger.info("this is reached")
        gate_query = await session.execute(
            select(Gate)
            .where(Gate.phone_number == phone_number)
            .where(Gate.exited_at == None)
            .where(Gate.salon_id == salon_id)
            .where(Gate.presence_status == PresenceStatus.INSALON)
            .order_by(Gate.entered_at.desc())
        )
        logger.info("this is reached")
        sql_gate = await gate_query.scalar_one_or_none()
        return sql_gate
    except Exception as e:
        logger.info("the error in gate: {e}")