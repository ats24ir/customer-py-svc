from sqlalchemy import select, func, update
import logging
from datetime import datetime, timedelta
from database_models.databases_connections import redis, get_async_session
from database_models.alchemy_models import (
    Customer as SQLCustomer, CustomerGroup as SQLCustomerGroup,
    SalonCustomerGroup as SQLSalonCustomerGroup, ScoresWallet as SQLScoresWallet,
    ScoresReceipt as SQLScoresReceipt, IncomePrizes, OutcomePrize, PrizeWallets
)
from database_models.pydantic_models import *
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
from redis.asyncio import Redis
import asyncio

async def find_customer_placement(phone_number, salon_id, session):
    try:
        # Fetch customer points
        scores_wallet_query = await session.execute(
            select(SQLScoresWallet.in_to_scores_wallet)
            .filter(SQLScoresWallet.phone_number == phone_number)
        )
        customer_points = scores_wallet_query.scalar_one_or_none()
        print(customer_points,salon_id)
        if customer_points is None:
            raise ValueError(f"No ScoresWallet found for customer with ID {phone_number}")

        # Fetch customer groups
        groups_query = await session.execute(
            select(SQLCustomerGroup)
            .join(SQLSalonCustomerGroup, SQLCustomerGroup.id == SQLSalonCustomerGroup.group_id)
            .filter(SQLSalonCustomerGroup.salon_id == int(salon_id))
            .filter(SQLCustomerGroup.points_needed <= customer_points)
            .order_by(SQLCustomerGroup.points_needed.desc())
        )
        groups = groups_query.scalars().all()
        print(groups)
        # Fetch customer details
        customer_query = await session.execute(
            select(SQLCustomer).filter(SQLCustomer.phone_number == phone_number)
        )
        customer = customer_query.scalar_one_or_none()
        print(customer)
        if not customer:
            raise ValueError(f"No customer found with ID {phone_number}")

        if groups:
            highest_group = groups[0]
            print(highest_group)
            return highest_group
        else:
            raise ValueError

    except Exception as e:
        logger.error(f"Error finding customer placement: {e}")
        raise


async def prize_balance_receipt_charge(phone_number, salon_id, total_spent, session,redis, invoice_id):
    try:
        group = await find_customer_placement(phone_number, salon_id, session)
        amount = int(group.to_prize_balance_percentage * total_spent / 100)

        # Create income receipt
        income_receipt = IncomePrizes(
            amount=amount,
            created_at=datetime.now(),
            phone_number=phone_number,
            salon_id=salon_id,
            remaining_amount=amount,
            expire_date=datetime.now() + timedelta(days=group.cashback_expire_in_days),
            awarded_for_invoice_id=invoice_id
        )
        session.add(income_receipt)

        # Fetch or create prize wallet
        prize_wallet = await session.execute(
            select(PrizeWallets)
            .filter_by(customer_phone_number=phone_number, salon_id=salon_id)
        )
        prize_wallet = prize_wallet.scalar_one_or_none()

        if prize_wallet:
            await session.execute(
                update(PrizeWallets)
                .where(PrizeWallets.id == prize_wallet.id)
                .values(balance=PrizeWallets.balance + amount)
            )
        else:
            prize_wallet = PrizeWallets(
                customer_phone_number=phone_number,
                salon_id=salon_id,
                balance=amount
            )
            session.add(prize_wallet)
        await session.flush()
        # await session.commit()

        #Redis Implantation
        redis_income_prize = IncomePrize(
            id=income_receipt.id,
            amount=amount,
            created_at=income_receipt.created_at.strftime("%Y-%m-%d %H:%M"),
            phone_number=phone_number,
            salon_id=salon_id,
            expires_at=income_receipt.expire_date.strftime("%Y-%m-%d %H:%M"),
            awarded_for_invoice_id=invoice_id,
            remaining_amount=amount,
        )

        redis_salon_wallet = await redis.json().get(f"models.SalonPrizeWallet:{phone_number}-{salon_id}")
        if redis_salon_wallet:
            new_balance = redis_salon_wallet["balance"] +amount
            await redis.json().set(f"models.SalonPrizeWallet:{phone_number}-{salon_id}", "$.balance", new_balance)
        else:
            redis_salon_wallet = SalonPrizeWallet(
                id = prize_wallet.id,
                balance = amount,
                salon_id = salon_id,
                phone_number = phone_number,
            )
            await redis.json().set(f"models.SalonPrizeWallet:{phone_number}-{salon_id}", "$", redis_salon_wallet.dict())
        await redis.json().set(f"models.PrizeIncome:{phone_number}-{salon_id}-{income_receipt.id}", "$", redis_income_prize.dict())

    except Exception as e:
        await session.rollback()
        raise e


async def salon_prize_wallet_discount_calculator(total_cost_of_services, phone_number, salon_id, session):
    try:
        group = await find_customer_placement(phone_number, salon_id, session)
        total_discount_possible = int(group.prize_wallet_usage_ratio * total_cost_of_services / 100)
        logger.info(f"The total discount possible is {total_discount_possible}")
        return total_discount_possible

    except Exception as e:
        logger.error(f"Error calculating discount: {e}")
        raise e


async def prize_balance_receipt_use(total_cost_of_services, phone_number, salon_id, session,redis, invoice_id):
    try:
        total_discount_possible = await salon_prize_wallet_discount_calculator(
            total_cost_of_services, phone_number, salon_id, session
        )
        logger.info(f"The Calculator returns this ==================>>> {total_discount_possible}")

        # Fetch prize wallet
        prize_wallet = await session.execute(
            select(PrizeWallets)
            .filter_by(customer_phone_number=phone_number, salon_id=salon_id)
        )
        prize_wallet = prize_wallet.scalar_one_or_none()

        if not prize_wallet or prize_wallet.balance == 0:
            return total_cost_of_services

        total_balance = prize_wallet.balance
        print(f"this the the total balance inside the use function {total_balance}")

        # Fetch eligible receipts
        receipts_query = await session.execute(
            select(IncomePrizes)
            .where(IncomePrizes.salon_id == salon_id)
            .where(IncomePrizes.phone_number == phone_number)
            .where(IncomePrizes.remaining_amount > 0)
            .where(IncomePrizes.expire_date > datetime.now())
            .order_by(IncomePrizes.expire_date.asc())
        )
        receipts = receipts_query.scalars().all()


        remaining_discount = total_discount_possible
        for receipt in receipts:
            if receipt.remaining_amount >= remaining_discount:
                receipt.remaining_amount -= remaining_discount
                outcome_receipt = OutcomePrize(
                    phone_number=phone_number,
                    created_at=datetime.now(),
                    amount=remaining_discount,
                    invoice_spent_on=invoice_id,
                    income_id=receipt.id
                )
                session.add_all([receipt, outcome_receipt])
                break
            elif receipt.remaining_amount < remaining_discount:
                remaining_discount -= receipt.remaining_amount
                outcome_receipt = OutcomePrize(
                    phone_number=phone_number,
                    created_at=datetime.now(),
                    amount=receipt.remaining_amount,
                    invoice_spent_on=invoice_id,
                    income_id=receipt.id
                )
                receipt.remaining_amount = 0
                session.add_all([receipt, outcome_receipt])

        total_discount_applied = total_discount_possible - remaining_discount
        prize_wallet.balance = max(0, prize_wallet.balance - total_discount_applied)
        session.add(prize_wallet)

        print(f"this is the output of the use function {total_cost_of_services - remaining_discount}")
        return total_cost_of_services - remaining_discount

    except Exception as e:
        logger.error(f"Error in salon_prize_wallet_use: {e}")
        await session.rollback()
        raise e


async def earn_scores(phone_number, paid_price, session,redis):
    try:
        # Fetch scores wallet
        scores_wallet_query = await session.execute(
            select(SQLScoresWallet).where(SQLScoresWallet.phone_number == phone_number)
        )
        scores_wallet = scores_wallet_query.scalar_one_or_none()

        if not scores_wallet:
            raise ValueError("Scores wallet not found.")

        # Calculate earned score
        earned_score = int(paid_price / 1000)
        new_score = scores_wallet.in_to_scores_wallet + earned_score

        # Update scores wallet
        await session.execute(
            update(SQLScoresWallet)
            .where(SQLScoresWallet.id == scores_wallet.id)
            .values(in_to_scores_wallet=new_score)
        )

        # Create score receipt
        score_receipt = SQLScoresReceipt(
            is_spent=False,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            phone_number=phone_number,
            amount=earned_score
        )
        session.add(score_receipt)

        # Update in Redis
        score_wallet_key = f"ScoresWallets:{phone_number}"
        score_wallet_data = await redis.json().get(score_wallet_key)
        if score_wallet_data:
            score_wallet_data['in_to_scores_wallet'] = new_score
            await redis.json().set(score_wallet_key, "$", score_wallet_data)
            await redis.json().set(f"ScoresReceipts:{phone_number}:", "$", score_receipt.__dict__)
        else:
            logger.warning(f"Customer with phone_number {phone_number} not found in Redis for updating scores.")

        await session.commit()

    except Exception as e:
        logger.error(f"Error updating customer scores: {e}")
        await session.rollback()
        raise e

async def main():
    # Initialize the async session and Redis connection
    async with get_async_session() as session:
        redis = Redis(
            host='192.168.16.143',
            port=6290,
            db=0,
            password=None,
            decode_responses=False
        )

        # Example data
        phone_number = "09011401001"
        salon_id = 1
        total_spent = 1000
        invoice_id = 5

        try:
            # Call the prize_balance_receipt_charge function
            await prize_balance_receipt_charge(phone_number, salon_id, total_spent, session, redis, invoice_id)
            print("Prize balance receipt charge processed successfully.")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            await session.commit()

# Run the async main function
# asyncio.run(main())