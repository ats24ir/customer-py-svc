from redis.asyncio import Redis
from databases_connections import redis as redis_client
import asyncio

async def setup_indexes(redis_client):
    # Receipts Index
    await redis_client.execute_command(
        "FT.CREATE", "models.Receipts:index", "ON", "JSON", "PREFIX", "1", "models.Receipts:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.amount", "AS", "amount", "NUMERIC",
        "$.wallet_id", "AS", "wallet_id", "TAG",
        "$.created_at", "AS", "created_at", "TEXT",
        "$.is_spent", "AS", "is_spent", "TAG",
        "$.phone_number", "AS", "phone_number", "TAG"
    )

    # Invoices Index
    await redis_client.execute_command(
        "FT.CREATE", "models.Invoices:index", "ON", "JSON", "PREFIX", "1", "models.Invoices:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.total_amount", "AS", "total_amount", "NUMERIC",
        "$.created_at", "AS", "created_at", "TEXT",
        "$.services_id", "AS", "services_id", "TAG",
        "$.phone_number", "AS", "phone_number", "TAG",
        "$.status", "AS", "status", "TAG"
    )

    # Services Index
    await redis_client.execute_command(
        "FT.CREATE", "models.Services:index", "ON", "JSON", "PREFIX", "1", "models.Services:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.name", "AS", "name", "TEXT",
        "$.price", "AS", "price", "NUMERIC",
        "$.duration", "AS", "duration", "NUMERIC",
        "$.category_id", "AS", "category_id", "TAG",
        "$.descriptions", "AS", "descriptions", "TEXT"
    )

    # Artists Index
    await redis_client.execute_command(
        "FT.CREATE", "models.Artists:index", "ON", "JSON", "PREFIX", "1", "models.Artists:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.name", "AS", "name", "TEXT", "SORTABLE",
        "$.age", "AS", "age", "NUMERIC", "SORTABLE",
        "$.city", "AS", "city", "TEXT", "SORTABLE",
        "$.services_ids", "AS", "services_ids", "TAG",
        "$.salons_ids", "AS", "salons_ids", "TAG",
    )

    # Wallets Index
    await redis_client.execute_command(
        "FT.CREATE", "models.Wallets:index", "ON", "JSON", "PREFIX", "1", "models.Wallets:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.in_to_wallet", "AS", "in_to_wallet", "NUMERIC",
        "$.out_of_wallet", "AS", "out_of_wallet", "NUMERIC",
        "$.customer_id", "AS", "customer_id", "NUMERIC"
    )

    # SalonPrizeWallet Index
    await redis_client.execute_command(
        "FT.CREATE", "models.SalonPrizeWallet:index", "ON", "JSON", "PREFIX", "1", "models.SalonPrizeWallet:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.in_to_prize_balance", "AS", "in_to_prize_balance", "NUMERIC",
        "$.out_of_prize_balance", "AS", "out_of_prize_balance", "NUMERIC",
        "$.in_to_timed_prize_balance", "AS", "in_to_timed_prize_balance", "NUMERIC",
        "$.out_of_timed_prize_balance", "AS", "out_of_timed_prize_balance", "NUMERIC",
        "$.salon_id", "AS", "salon_id", "TAG",
        "$.customer_id", "AS", "customer_id", "TAG"
    )

    # ScoresWallets Index
    await redis_client.execute_command(
        "FT.CREATE", "models.ScoresWallets:index", "ON", "JSON", "PREFIX", "1", "models.ScoresWallets:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.in_to_scores_wallet", "AS", "in_to_scores_wallet", "NUMERIC",
        "$.out_of_scores_balance", "AS", "out_of_scores_balance", "NUMERIC",
        "$.customer_id", "AS", "customer_id", "TAG"
    )

    # ScoresWalletReceipt Index
    await redis_client.execute_command(
        "FT.CREATE", "models.ScoresWalletReceipt:index", "ON", "JSON", "PREFIX", "1", "models.ScoresWalletReceipt:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.is_spent", "AS", "is_spent", "TAG",
        "$.amount", "AS", "amount", "NUMERIC",
        "$.created_at", "AS", "created_at", "TEXT",
        "$.customer_id", "AS", "customer_id", "TAG"
    )

    # CustomerGroups Index
    await redis_client.execute_command(
        "FT.CREATE", "models.CustomerGroups:index", "ON", "JSON", "PREFIX", "1", "models.Groups:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.name", "AS", "name", "TEXT",
        "$.pay_free_reserve", "AS", "pay_free_reserve", "TAG",
        "$.to_prize_wallet_percentage", "AS", "to_prize_wallet_percentage", "NUMERIC",
        "$.to_timed_prize_wallet_percentage", "AS", "to_timed_prize_wallet_percentage", "NUMERIC",
        "$.prize_wallet_usage_ratio", "AS", "prize_wallet_usage_ratio", "NUMERIC",
        "$.salon_id", "AS", "salon_id", "TAG",
        "$.points_needed", "AS", "points_needed", "NUMERIC"
    )

    # Customers Index
    await redis_client.execute_command(
        "FT.CREATE", "models.Customers:index", "ON", "JSON", "PREFIX", "1", "models.Customers:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.name", "AS", "name", "TEXT",
        "$.age", "AS", "age", "NUMERIC",
        "$.city", "AS", "city", "TEXT",
        "$.phone_number", "AS", "phone_number", "TAG",
        "$.birthday", "AS", "birthday", "TEXT",
        "$.marriage_anniversary", "AS", "marriage_anniversary", "TEXT",
        "$.special_days", "AS", "special_days", "TAG",
        "$.secondary_phone_number", "AS", "secondary_phone_number", "TAG"
    )

    # Salons Index
    await redis_client.execute_command(
        "FT.CREATE", "models.Salons:index", "ON", "JSON", "PREFIX", "1", "models.Salons:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.name", "AS", "name", "TEXT",
        "$.age", "AS", "age", "NUMERIC",
        "$.city", "AS", "city", "TEXT",
    )

    # OTP Index
    await redis_client.execute_command(
        "FT.CREATE", "models.OTP:index", "ON", "JSON", "PREFIX", "1", "models.OTP:",
        "SCHEMA",
        "$.otp", "AS", "otp", "TAG",
    )

    # Sessions Index
    await redis_client.execute_command(
        "FT.CREATE", "models.Sessions:index", "ON", "JSON", "PREFIX", "1", "models.Sessions:",
        "SCHEMA",
        "$.phoneNumber", "AS", "phoneNumber", "TAG",
    )
    await redis_client.execute_command(
        "FT.CREATE", "models.ServiceCategory:index", "ON", "JSON", "PREFIX", "1", "models.ServiceCategory:",
        "SCHEMA",
        "$.name", "AS", "name", "TEXT",
        "$.id", "AS", "id", "TAG",

    )
    # Reserve Index
    await redis_client.execute_command(
        "FT.CREATE", "models.Reserves:index", "ON", "JSON", "PREFIX", "1", "models.Reserves:",
        "SCHEMA",
        "$.id", "AS", "id", "TAG",
        "$.time", "AS", "time", "TEXT",
        "$.time_jalali", "AS", "time_jalali", "TEXT",
        "$.start_stamp", "AS", "start_stamp", "NUMERIC",
        "$.end_stamp", "AS", "end_stamp", "NUMERIC",
        "$.available", "AS", "available", "TAG",
        "$.salon_id", "AS", "salon_id", "TAG",
        "$.salon_name", "AS", "salon_name", "TEXT",
        "$.artist_id", "AS", "artist_id", "TAG",
        "$.artist_name", "AS", "artist_name", "TEXT",
        "$.service_id", "AS", "service_id", "TAG",
        "$.service_name", "AS", "service_name", "TEXT",
        "$.phone_number", "AS", "phone_number", "TAG",
        "$.reserved_at_datetime", "AS", "reserved_at_datetime", "TEXT",
        "$.reserved_at_timestamp", "AS", "reserved_at_timestamp", "NUMERIC",
        "$.reserved_at_jalali", "AS", "reserved_at_jalali", "TEXT",
        "$.reserved_at", "AS", "reserved_at", "TEXT"
    )


    print("All indexes have been created successfully.")

async def main():
    await setup_indexes(redis_client)

if __name__ == "__main__":
    asyncio.run(main())