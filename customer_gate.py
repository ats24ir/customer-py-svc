from database_models.alchemy_models import Gate, GateType, Invoice
from database_models.databases_connections import get_sync_session as sessions,redis
from datetime import datetime
from sqlalchemy import  select
from login_logic.customer_create import customer_get_or_create

def entry_gate(phone_number,salon_id,operator=None, reserve_id=None):
    with sessions() as session:
        try:
            customer_get_or_create(phone_number, session, redis)
            new_entry = Gate(
                phone_number=phone_number,
                entered_at=datetime.now(),
                salon_id=salon_id,
                type=GateType.RESERVED if reserve_id else GateType.UNRESERVED,
                reserve_id=reserve_id if reserve_id else None,
                operator = operator if operator else "Reservation"
            )
            session.add(new_entry)
            session.commit()
            return new_entry
        except Exception as e:
            print(f"The error in gate: {e}")

def exit_gate(phone_number):
    with sessions() as session:
        try:
            gate_query = session.execute(
                select(Gate).where(Gate.phone_number == phone_number)
                .where(Gate.exited_at == None)
                .where(Gate.presence_status == "InSalon")
                .order_by(Gate.entered_at.desc())
            )
            sql_gate = gate_query.scalar_one_or_none()
            if not sql_gate:
                raise ValueError ("you have no entry")

            if sql_gate.invoice_id:
                invoice_query = session.execute(
                    select(Invoice).where(Invoice.phone_number == phone_number)
                )
                sql_invoice = invoice_query.scalar_one_or_none()
                if sql_invoice.status == "Pending":
                    raise ValueError ("you have pending invoice")
            sql_gate.exited_at = datetime.now()
            sql_gate.presence_status = "Exited"
            session.add(sql_gate)
            session.commit()
        except Exception as e:
            print(f"The error in gate: {e}")

