from database_models.pydantic_models import Receipts
from sqlalchemy import select, update
from database_models.alchemy_models import Wallet as SQLWallet, Receipts as SQLReceipts, Invoice as SQLInvoice,Reserved as SQLReserved
from datetime import datetime
from database_models.databases_connections import get_async_session, redis as redis_client
import asyncio

async def create_into_wallet_receipts(session, phone_number, amount):
    try:
        wallet_query = await session.execute(
            select(SQLWallet).where(SQLWallet.phone_number == phone_number)
        )
        sql_wallet = wallet_query.scalar_one_or_none()
        if not sql_wallet:
            raise ValueError(f"No wallet found for customer {phone_number}")

        sql_wallet_id = sql_wallet.id

        new_receipt = SQLReceipts(
            amount=amount,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            phone_number=phone_number,
            is_spent=False,
            wallet_id=sql_wallet_id
        )
        session.add(new_receipt)
        await session.flush()

        await session.execute(
            update(SQLWallet)
            .where(SQLWallet.id == sql_wallet_id)
            .values(in_to_wallet=SQLWallet.in_to_wallet + amount)
        )

        await session.commit()

        redis_customer = await redis_client.json().get(f"models.Customers:{phone_number}")
        if not redis_customer:
            raise ValueError(f"No customer found in Redis with ID {phone_number}")

        phone_number = redis_customer["phone_number"]

        redis_receipt = Receipts(
            id=str(new_receipt.id),
            amount=amount,
            wallet_id=str(sql_wallet_id),
            created_at=new_receipt.created_at,
            is_spent=False,
            phone_number=str(phone_number),
        )

        await redis_client.json().set(f"models.Receipts:{new_receipt.id}", "$",
                                   redis_receipt.model_dump())

        await redis_client.json().set(f"models.Wallets:{phone_number}", "$.in_to_wallet",
                                   sql_wallet.in_to_wallet + amount)

    finally:
        await redis_client.close()

async def create_out_of_wallet_receipts_for_reserved(session, phone_number, amount, reserve_id):
    try:
        # Ensure the reserve_id exists in the reserved table
        reserve_query = await session.execute(
            select(SQLReserved).where(SQLReserved.id == reserve_id)
        )
        reserve = reserve_query.scalar_one_or_none()
        if not reserve:
            raise ValueError(f"No reserve found with ID {reserve_id}")

        wallet_query = await session.execute(
            select(SQLWallet).where(SQLWallet.phone_number == phone_number)
        )
        sql_wallet = wallet_query.scalar_one_or_none()
        if not sql_wallet:
            raise ValueError(f"No wallet found for customer {phone_number}")

        sql_wallet_id = sql_wallet.id

        # Create receipt
        new_receipt = SQLReceipts(
            amount=amount,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            phone_number=phone_number,
            is_spent=True,
            reserve_id=reserve_id,
            wallet_id=sql_wallet_id
        )
        session.add(new_receipt)

        # Update wallet balance
        await session.execute(
            update(SQLWallet)
            .where(SQLWallet.id == sql_wallet_id)
            .values(out_of_wallet=SQLWallet.out_of_wallet + amount)
        )

        await session.commit()

        # Redis Interaction (commented out for now)
        # redis_receipt = Receipts(
        #     id=str(new_receipt.id),
        #     amount=amount,
        #     wallet_id=str(sql_wallet_id),
        #     created_at=new_receipt.created_at,
        #     is_spent=True,
        #     phone_number=str(redis_customer["phone_number"]),
        # )
        #
        # await redis_client.json().set(f"models.Receipts:{new_receipt.id}", "$",
        #                            redis_receipt.model_dump())
        #
        # await redis_client.json().set(f"models.Wallets:{phone_number}", "$.out_of_wallet",
        #                            sql_wallet.out_of_wallet + amount)

    except Exception as e:
        print(f"the error in payment use function {e}")

# async def main():
#     async with get_async_session() as session:
#         try:
#             # Example usage of create_into_wallet_receipts
#             await create_into_wallet_receipts(session, "09011401001", 100.0)
#
#             # Example usage of create_out_of_wallet_receipts_for_reserved
#             await create_out_of_wallet_receipts_for_reserved(session, "09011401001", 50.0, 1)
#         except Exception as e:
#             print(f"An error occurred: {e}")
#
# # Run the async main function
# asyncio.run(main())