from sqlalchemy import select
from database_models.pydantic_models import Customers, Wallets, ScoresWallets
from database_models.alchemy_models import Customer, Wallet, ScoresWallet


async def customer_get_or_create(phone_number, session, redis):
    result = await session.execute(select(Customer).filter_by(phone_number=phone_number))
    existing_customer = result.scalars().first()

    if existing_customer:
        return

    sql_customer = Customer(phone_number=phone_number)
    session.add(sql_customer)
    await session.flush()

    sql_wallet = Wallet(customer_id=sql_customer.id, phone_number=phone_number)
    session.add(sql_wallet)

    sql_scores_wallet = ScoresWallet(phone_number=sql_customer.phone_number)
    session.add(sql_scores_wallet)


    await session.commit()


    customer = Customers(
        id=str(sql_customer.id),
        phone_number=str(phone_number),
    )

    scores_wallet = ScoresWallets(
        id=str(sql_scores_wallet.id),
        customer_id=str(sql_customer.id)
    )

    wallet = Wallets(
        id=str(sql_wallet.id),
        in_to_wallet=0,
        out_of_wallet=0,
        customer_id=str(sql_customer.id),
        phone_number=phone_number
    )

    await redis.json().set(f"models.Customers:{customer.phone_number}", "$", customer.dict())
    await redis.json().set(f"models.ScoresWallets:{customer.phone_number}", "$", scores_wallet.dict())
    await redis.json().set(f"models.Wallets:{customer.phone_number}", "$", wallet.dict())