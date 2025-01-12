import jdatetime
from customer_transactions.prizes_logic import *
from database_models.alchemy_models import Reserved as SQLReserved, Customer as SQLCustomer, Salon as SQLSalon, Artist as SQLArtist, Service as SQLService, Wallet as SQLWallet
from sqlalchemy import select
from datetime import datetime
from database_models.databases_connections import get_async_session, redis
from customer_transactions.payment_receipts import create_out_of_wallet_receipts_for_reserved, create_into_wallet_receipts

async def single_reserve(session, reserve_id):
    try:
        reserve = await redis.json().get(f"models.Reserves:{reserve_id}")
        phone_number = reserve["phone_number"]
        service_id = reserve["service_id"]
        salon_id = reserve["salon_id"]
        artist_id = reserve["artist_id"]
        print(f"redis reserve id is {reserve["id"]}")
        print(salon_id, artist_id, service_id)

        if reserve is None:
            print(f"No reserves found for id: {reserve}")
            return
        time_str = reserve["time"]
        time_datetime = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        timestamps = time_datetime.timestamp()
        print("the point is reached")

        sql_customer_query = await session.execute(
            select(SQLCustomer).where(SQLCustomer.phone_number == phone_number)
        )
        sql_customer =  sql_customer_query.scalar_one_or_none()
        print(f"SQL Customer: {sql_customer}")
        if sql_customer is None:
            raise ValueError(f"No customer found with phone number: {phone_number}")

        sql_salon_query = await session.execute(
            select(SQLSalon).where(SQLSalon.id == int(salon_id))
        )
        sql_salon = sql_salon_query.scalar_one_or_none()
        print(f"SQL Salon: {sql_salon}")
        if sql_salon is None:
            raise ValueError(f"No salon found with ID: {salon_id}")

        sql_artist_query = await session.execute(
            select(SQLArtist).where(SQLArtist.id == int(artist_id))
        )
        sql_artist = sql_artist_query.scalar_one_or_none()
        print(f"SQL Artist: {sql_artist}")
        if sql_artist is None:
            raise ValueError(f"No artist found with ID: {artist_id}")

        sql_service_query = await session.execute(
            select(SQLService).where(SQLService.id == int(service_id))
        )
        sql_service = sql_service_query.scalar_one_or_none()
        print(f"SQL Service: {sql_service}")  # Debug print
        if sql_service is None:
            raise ValueError(f"No service found with ID: {service_id}")

        sql_wallet_query = await session.execute(
            select(SQLWallet).where(SQLWallet.phone_number == phone_number)
        )
        sql_wallet = sql_wallet_query.scalar_one_or_none()
        print(f"SQL Wallet: {sql_wallet}")  # Debug print
        if sql_wallet is None:
            raise ValueError(f"No wallet found for phone number: {phone_number}")
        print("this is not reached")

        pay_able_price = sql_service.price

        group = await find_customer_placement(sql_customer.phone_number, sql_salon.id, session)
        pre_paid_amount = int((pay_able_price / 100)) * group.pre_pay_percentage


        # Create Reserves in PostgreSQL
        new_reserve = SQLReserved(
            id=int(reserve["id"]),
            time=time_datetime,
            time_jalali=jdatetime.datetime.fromtimestamp(timestamps).togregorian(),
            salon_id=sql_salon.id,
            artist_id=sql_artist.id,
            service_id=sql_service.id,
            phone_number=sql_customer.phone_number,
            pre_paid_amount=pre_paid_amount,
            reserved_at_datetime=datetime.now(),
            reserved_at_timestamp=int(datetime.now().timestamp()),
            reserved_at_jalali=jdatetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            reserved_at=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        session.add(new_reserve)
        await session.flush()

        # the partial pay
        print(f"new reserve id is {new_reserve.id}")
        if sql_wallet.balance >= pre_paid_amount:
            await create_out_of_wallet_receipts_for_reserved(session, phone_number, pre_paid_amount, new_reserve.id)

        elif sql_wallet.balance < pre_paid_amount:
            price_left = sql_wallet.balance - pre_paid_amount
            # Send To Payment Gate Here
            await create_into_wallet_receipts(session, phone_number, price_left)
            await create_out_of_wallet_receipts_for_reserved(session, phone_number, pre_paid_amount, new_reserve.id)

        if not all([sql_customer, sql_salon, sql_artist, sql_service]):
            raise ValueError("Some of the required entities were not found.")


        await session.commit()

    except Exception as e:
        print(f"the error : {e}")
        await session.rollback()

async def main():
    async with get_async_session() as session:
        try:
            await single_reserve(session, 2)
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())