import json
import asyncio
from aio_pika import connect, Message, ExchangeType
import time as timestamp
import jdatetime

from customer_transactions.prizes_logic import *
from database_models.pydantic_models import *
from aio_pika.abc import AbstractExchange
from database_models.databases_connections import get_prisma

default_exchange: AbstractExchange = None


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def get_available_sequences(services_ids, salon_id):
    print("entering the available seq")
    async with get_prisma() as prisma_manager:
        prisma = prisma_manager.get_prisma()
        try:
            # Convert string IDs to integers
            services_ids = [int(service_id) for service_id in services_ids]
        except ValueError:
            return {"error": "Invalid service ID format. Must be integers."}
        try:
           salon_id = int(salon_id)
        except ValueError:
             return {"error": "Invalid salon ID format. Must be an integer."}
        services = await prisma.service.find_many(where={"id": {"in": services_ids}})
        if len(services) != len(services_ids):
            return {"error": "One or more services not found"}

        salon = await prisma.salon.find_unique(where={"id": salon_id})
        if not salon:
            return {"error": "Salon not found"}

    async with await get_redis_client() as redis:
        # Retrieve document IDs from FT.SEARCH
        search_results = await asyncio.gather(*[
            redis.execute_command(
                "FT.SEARCH", "timeblocks_idx",
                f"@service_id:{{{s.id}}} @salon_id:{{{salon_id}}} @available:{{True}}",
                "LIMIT", "0", "2000"
            )
            for s in services
        ])


        document_ids = []
        for result in search_results:
            # Here, result[0] is the count, and every two elements after are id and content
            for i in range(1, len(result), 2):  # Step by 2 to get every ID
                document_ids.append(result[i])

        # Use JSON.GET to retrieve the full JSON data for each document ID
        all_json_blocks = await asyncio.gather(*[
            redis.execute_command("JSON.GET", doc_id) for doc_id in document_ids
        ])

        # Parse results into Python dictionaries
        all_blocks = [json.loads(block) for block in all_json_blocks if block]



        def extract_time_artist(json_str):
          try:
             timeblock_data=json.loads(json_str)
             time=datetime.strptime(timeblock_data["time"],"%Y-%m-%d %H:%M")
             return time,timeblock_data["artist_id"]
          except (TypeError, ValueError, json.JSONDecodeError,KeyError):
             return None

        service_blocks = {
            service.id: sorted(
               [result for result in [extract_time_artist(block) for block in blocks] if result is not None ]
            )
           for service, blocks in all_blocks
       }


        print(all_blocks)
    time_between = timedelta(minutes=40)
    result = []

    print(service_blocks)
    for start_time, artist_id in service_blocks[services[0].id]:
        sequence = [(services[0].id, start_time, artist_id)]
        current_time = start_time + timedelta(minutes=services[0].duration)

        for service in services[1:]:
            match = next(
                ((time, artist_id) for time, artist_id in service_blocks[service.id] if
                 current_time <= time <= current_time + time_between),
                None
            )
            if match:
                time, artist_id = match
                sequence.append((service.id, time, artist_id))
                current_time = time + timedelta(minutes=service.duration)
            else:
                break

        if len(sequence) == len(services):
            result.append(sequence)
        print(f"the result is {result}")
    return [
        [(service_id, time.strftime("%Y-%m-%d %H:%M"), artist_id) for service_id, time, artist_id in seq]
        for seq in result
    ]


async def create_sequence_object(customer_id, time_blocks):
    async with get_prisma() as prisma_manager:
        prisma = prisma_manager.get_prisma()
        seq = await prisma.sequence.create(data={
            'customerId': int(customer_id),
            'timeBlocks': {
                'connect': [{'id': int(tb.id)} for tb in time_blocks]
            }
        })

    async with await get_redis_client() as redis:
        redis_customer = await redis.json().get(f"models.Customers:{customer_id}")
        if redis_customer:
            redis_sequence = Sequence(
                id=str(seq.id),
                time_blocks_ids=[tb.id for tb in time_blocks],
                customer=Customers(**redis_customer[0])
            )
            await redis.json().set(f"models.Sequence:{seq.id}", "$", redis_sequence.dict())


async def reserve_sequence(sequence, customer_id, salon_id, prize_wallet_usage):
    async with get_prisma() as prisma_manager:
        prisma = prisma_manager.get_prisma()
        customer = await prisma.customer.find_unique(where={"id": int(customer_id)})
        if not customer:
            return {"error": "Customer not found"}

        async def reserve_block(service_name, time_str, artist):
            time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            block = await prisma.timeblock.find_first(
                where={
                    "time": time,
                    "service": {"name": service_name},
                    "artist": {"name": artist},
                    "salonId": int(salon_id),
                    "available": True
                }
            )
            if not block:
                return None

            await prisma.timeblock.update(
                where={"id": block.id},
                data={
                    "available": False,
                    "customerId": customer.id,
                    "reservedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "reservedAtTimestamp": int(timestamp.time()),
                    "reservedAtJalali": jdatetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "reservedAtDatetime": datetime.now(),
                }
            )
            return block

        reserved_blocks = await asyncio.gather(*[
            reserve_block(service_name, time_str, artist) for service_name, time_str, artist in sequence
        ])
        reserved_blocks = [b for b in reserved_blocks if b is not None]

        if not reserved_blocks:
            return {"error": "No valid time blocks available for reservation"}

        await create_sequence_object(customer_id, reserved_blocks)
        await salon_prize_wallet_create(salon_id=str(salon_id), customer_id=str(customer_id))
        pay_price = await payable_price(prize_wallet_usage, customer_id, salon_id, sequence)

        await prisma.wallet.update(
            where={"customerId": customer.id},
            data={"out_of_wallet": {"increment": pay_price}}
        )

        return {"success": "Sequence reserved successfully"}


async def price_calculation(sequence):
    total_price = 0
    async with await get_redis_client() as redis:
        for service_name, _, _ in sequence:
            service = await redis.json().get(f"models.Services:*")
            if service:
                service = next((s for s in [Services(**json.loads(s)) for s in service] if s.name == service_name),
                               None)
                if service:
                    total_price += service.price
    return total_price


async def price_and_permissions(sequence, customer_id, salon_id):
    total_price = await price_calculation(sequence)
    discount = await salon_prize_wallet_discount_calculator(total_price, customer_id, salon_id)
    return {
        "total_price": total_price,
        "discount_possible": discount,
        'price_after_discount': total_price - discount
    }


async def payable_price(wallet_usage, customer_id, salon_id, sequence):
    data = await price_and_permissions(sequence, customer_id, salon_id)
    async with get_prisma() as prisma_manager:
        prisma = prisma_manager.get_prisma()
        salon = await prisma.salon.find_unique(where={"id": salon_id},
                                               include={"groups": {"include": {"customers": True}}})
        group = next((g for g in salon.groups for c in g.customers if c.id == customer_id), None)

    if group is None or not group.pay_free_reserve:
        if wallet_usage == 1:
            await salon_prize_wallet_use(data["total_price"], customer_id, salon_id)
            await salon_prize_wallet_charge(customer_id, salon_id, data["price_after_discount"])
            return data['price_after_discount']
        elif wallet_usage == 0:
            await salon_prize_wallet_charge(customer_id, salon_id, data["total_price"])
            return data['total_price']
    else:
        await salon_prize_wallet_charge(customer_id, salon_id, data["total_price"])
        return 0


async def on_request(message):
    global default_exchange
    async with message.process():
        async with get_prisma() as prisma_manager:
            prisma = prisma_manager.get_prisma()
            try:
                data = json.loads(message.body)
                action = data.get('action')
                response = {"error": "Invalid action"}
                if action == 'get_services':
                    response = {"services": [s.id for s in await prisma.service.find_many()]}
                elif action == 'get_sequences':
                    response = await get_available_sequences(data['services'], data['salon_id'])
                elif action == 'reserve_sequence':
                    response = await reserve_sequence(
                        data['sequence'], data['customer_id'], data['salon_id'], int(data['prize_wallet_usage'])
                    )
                elif action == 'get_salons':
                    salons = await prisma.salon.find_many(include={"services": True})
                    print(salons)
                    services_needed = data.get('services', [])
                    required_services = set(map(int,services_needed))
                    print(required_services)
                    response = {
                        "salons_id": [
                            s.id for s in salons if required_services.issubset({int(service.id) for service in s.services})
                        ]
                    }
                    print(response)
                elif action == 'calculate':
                    response = await price_and_permissions(data['sequence'], data['customer_id'], data['salon_id'])

                await default_exchange.publish(
                    Message(
                        body=json.dumps(response).encode(),
                        correlation_id=message.correlation_id,
                        reply_to=message.reply_to,
                    ),
                    routing_key=message.reply_to,
                )

            finally:
                pass


async def main():
    global default_exchange
    connection = await connect("amqp://admin:admin@localhost/")
    try:
        channel = await connection.channel()
        exchange = await channel.declare_exchange('rpc_exchange', ExchangeType.DIRECT)
        default_exchange = channel.default_exchange
        queue = await channel.declare_queue('rpc_queue')
        await queue.bind(exchange, routing_key='rpc_queue')
        await queue.consume(on_request)

        logger.info("Awaiting RPC requests")
        while True:
            await asyncio.sleep(0.1)
    finally:
        await connection.close()


if __name__ == '__main__':
    asyncio.run(main())
