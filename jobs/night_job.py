from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
from collections import defaultdict
from database_models.alchemy_models import IncomePrizes, PrizeWallets
from database_models.databases_connections import engine
import asyncio

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def update_database():
    async with AsyncSessionLocal() as session:
        try:
            receipts_query = await session.execute(
                select(IncomePrizes)
                .where(IncomePrizes.remaining_amount > 0)
                .where(IncomePrizes.expire_date > datetime.now())
                .order_by(IncomePrizes.expire_date.asc())
            )
            receipts = receipts_query.scalars().all()

            if receipts:
                customer_receipts = defaultdict(list)
                for receipt in receipts:
                    customer_receipts[receipt.phonenumber].append(receipt)

                for customer_id, customer_receipts_list in customer_receipts.items():
                    print(f"Processing receipts for customer {customer_id}")
                    balance = 0
                    for receipt in customer_receipts_list:
                        balance += receipt.remaining_amount
                    prize_wallet_query = await session.execute(
                        select(PrizeWallets)
                        .filter_by(customer_phone_number=customer_id, salon_id=receipt.salon_id)
                    )
                    prize_wallet = prize_wallet_query.scalar_one_or_none()

                    if prize_wallet:
                        prize_wallet.balance = balance
                        session.add(prize_wallet)
                await session.commit()
                print(f"Database updated at {datetime.now()}")
            else:
                print("No receipts to update.")

        except Exception as e:
            await session.rollback()
            logging.error(f"Error updating database: {e}", exc_info=True)
        finally:
            await session.close()


async def main():

    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_database, 'cron', hour=0, minute=0)
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
