from database_models.alchemy_models import CustomerGroup as SQLCustomerGroup, SalonCustomerGroup as SQLSalonCustomerGroup
from database_models.databases_connections import get_async_session as sessions, redis
from database_models.pydantic_models import CustomerGroups
from customer_transactions.prizes_logic import logger
import asyncio


async def create_group_for_customers(
    salon_id,
    name,
    pre_pay_percentage=20,
    to_prize_balance_percentage=50,
    prize_wallet_usage_ratio=50,
    points_needed=0,
    session=None,
    cashback_expire_in_days=30
):
    try:
        async with sessions() as session:
            sql_group = SQLCustomerGroup(
                name=name,
                to_prize_balance_percentage=to_prize_balance_percentage,
                prize_wallet_usage_ratio=prize_wallet_usage_ratio,
                pre_pay_percentage=pre_pay_percentage,
                points_needed=points_needed
            )
            session.add(sql_group)
            await session.flush()


            salon_group = SQLSalonCustomerGroup(salon_id=int(salon_id), group_id=sql_group.id)
            session.add(salon_group)

            await session.commit()

            logger.info(f"The SQL group is {sql_group}")
            logger.info(f"Salon ID after creating group: {salon_id}")


            redis_group = CustomerGroups(
                id=str(sql_group.id),
                name=name,
                to_prize_wallet_percentage=to_prize_balance_percentage,
                prize_wallet_usage_ratio=prize_wallet_usage_ratio,
                pre_pay_percentage=pre_pay_percentage,
                salon_id=str(salon_id),
                points_needed=points_needed
            )


            await redis.json().set(f"models.Groups:{sql_group.id}", "$", redis_group.dict())

            return sql_group.id

    except Exception as e:
        logger.error(f"Error creating group: {e}")
        raise

# async def main():
#     salon_id = 1
#     group_name = "VIP Customers"
#     group_id = await create_group_for_customers(salon_id=salon_id, name=group_name)
#     print(f"Created group with ID: {group_id}")
#
# # Run the async function
# asyncio.run(main())