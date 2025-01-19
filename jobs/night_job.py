from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
from collections import defaultdict
from database_models.alchemy_models import IncomePrizes, PrizeWallets, Gate, PresenceStatus
from database_models.databases_connections import engine
import asyncio

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def with_session(async_func):
    async with AsyncSessionLocal() as session:
        try:
            await async_func(session)
        except Exception as e:
            await session.rollback()
            logging.error(f"Error in {async_func.__name__}: {e}", exc_info=True)
        finally:
            await session.close()


async def update_database():
    await with_session(_update_database)


async def _update_database(session):
    receipts_query = await session.execute(
        select(IncomePrizes)
        .where(IncomePrizes.remaining_amount > 0)
        .where(IncomePrizes.expire_date > datetime.now())
        .order_by(IncomePrizes.expire_date.asc())
    )
    receipts = receipts_query.scalars().all()

    if receipts:

        customer_salon_receipts = defaultdict(list)
        for receipt in receipts:
            customer_salon_receipts[(receipt.phonenumber, receipt.salon_id)].append(receipt)

        for (customer_id, salon_id), receipts_list in customer_salon_receipts.items():
            print(f"Processing receipts for customer {customer_id} in salon {salon_id}")
            balance = 0
            for receipt in receipts_list:
                balance += receipt.remaining_amount

            prize_wallet_query = await session.execute(
                select(PrizeWallets)
                .filter_by(customer_phone_number=customer_id, salon_id=salon_id)
            )
            prize_wallet = prize_wallet_query.scalar_one_or_none()

            if prize_wallet:
                prize_wallet.balance = balance
                session.add(prize_wallet)

        await session.commit()
        print(f"Database updated at {datetime.now()}")
    else:
        print("No receipts to update.")


async def close_gates():
    await with_session(_close_gates)


async def _close_gates(session):
    gate_query = await session.execute(
        select(Gate)
        .where(Gate.presence_status == PresenceStatus.INSALON)
        .order_by(Gate.entered_at.desc())
    )
    sql_gates = gate_query.scalars().all()

    for gate in sql_gates:
        gate.presence_status = PresenceStatus.SYSTEMCLOSED
        session.add(gate)

    await session.commit()
    print(f"Closed {len(sql_gates)} gates at {datetime.now()}")


async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_database, 'cron', hour=0, minute=0)
    scheduler.add_job(close_gates, 'cron', hour=23, minute=59)
    scheduler.start()
    print("Press Ctrl+C to exit")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
