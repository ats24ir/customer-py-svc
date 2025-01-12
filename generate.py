from random import randint, choice, sample
import asyncio
import jdatetime
from redis.asyncio import Redis
from database_models.pydantic_models import *
from database_models.alchemy_models import *
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from customers_group import create_group_for_customers

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


engine = create_async_engine('postgresql+asyncpg://admin:admin@localhost:5432/mydatabase', echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# async def generate_time_blocks_for_month(salon: Salon, redis):
#     async def generate_time_blocks_for_artist_service(artist, service, session):
#         current_date = datetime.now()
#         end_date = current_date + timedelta(days=30)
#         start_hour = datetime.strptime(artist.working_hours["start"], "%H:%M")
#         end_hour = datetime.strptime(artist.working_hours["end"], "%H:%M")
#         duration = timedelta(minutes=service.duration)
#         counter = int((await redis.get("id_count")) or 0)
#         async with redis.pipeline() as pipe:
#             while current_date <= end_date:
#                 current_time = start_hour
#                 while current_time + duration <= end_hour:
#                     full_time = datetime.combine(current_date, current_time.time())
#
#                     time_block = TimeBlocks(
#                         id=str(counter),
#                         time=full_time.strftime("%Y-%m-%d %H:%M"),
#                         time_jalali=jdatetime.datetime.fromgregorian(datetime=full_time).strftime("%Y-%m-%d %H:%M"),
#                         start_stamp= full_time.timestamp(),
#                         end_stamp= (full_time+duration).timestamp(),
#                         available=True,
#                         salon_id=salon.id,
#                         salon_name=salon.name,
#                         artist_id=artist.id,
#                         artist_name=artist.name,
#                         service_id=service.id,
#                         service_name=service.name
#                     )
#                     key = f"{counter}"
#                     counter+=1
#                     await redis.set("id_count", str(counter))
#                     # Save time block to Redis
#                     await redis.json().set(f"models.TimeBlocks:{key}", "$", time_block.dict())
#                     current_time += duration
#                 current_date += timedelta(days=1)
#             await pipe.execute()
#
#     async with async_session() as session:
#      for service in salon.services:
#         for artist in salon.artists:
#             if service in artist.services:
#                 await generate_time_blocks_for_artist_service(artist, service,session)


class SalonDataGenerator:
    def __init__(self):
        self.service_names = [f"Service{i}" for i in range(10)]
        self.cities = ["Los Angeles", "New York", "Chicago", "Houston", "Phoenix"]
        self.service_list = []
        self.artists_list = []
        self.customers_id_list = []



    async def generate_services(self, redis):
       async with async_session() as session:
            for i in range(10):
                price = randint(1000, 20000)
                duration = randint(15, 180)

                options = [{'name': f"Option {j}", 'price': randint(5, 20)} for j in range(1, 4)]

                service = Services(id=str(i), name=self.service_names[i], price=price, duration=duration, options=options,
                                   )


                # Alchemy PG insert
                sql_service = Service(name=self.service_names[i], price=price, duration=duration)

                for option_data in options:
                    sql_option = ServiceOption(name=option_data['name'], price=option_data['price'])
                    sql_service.options.append(sql_option)
                session.add(sql_service)
                await session.flush()
                service.id = str(sql_service.id)

                self.service_list.append(service)
                await redis.json().set(f"models.Services:{service.id}", "$", service.dict())
            await session.commit()




    async def generate_artists(self, redis):
        async with async_session() as session:
            for i in range(1, 51):
                city = choice(self.cities)

                num_services = randint(1, min(5, len(self.service_list)))
                services = sample(self.service_list, num_services)
                services=list(services)

                start_hour = randint(8, 11)
                end_hour = start_hour + 8
                working_hours = {"start": f"{start_hour:02d}:00", "end": f"{end_hour:02d}:00"}
                artist = Artists(id=str(i), name=f"Artist {i}", age=randint(20, 50), services=services, city=city,
                                 working_hours=working_hours)

                # Alchemy PG insert
                sql_artist = Artist(name=f"Artist {i}", age=randint(20, 50), city=city, working_hours=working_hours)
                for service in services:
                    sql_service = await session.get(Service, int(service.id))
                    sql_artist.services.append(sql_service)
                session.add(sql_artist)
                await session.flush()
                artist.id = str(sql_artist.id)  # Update the pydantic model id with the db id

                self.artists_list.append(artist)
                # Save artist to Redis
                await redis.json().set(f"models.Artists:{artist.id}", "$", artist.dict())
            await session.commit()



    async def generate_customers(self, redis):
        async with async_session() as session:
            for i in range(1, 51):
                city = choice(self.cities)
                balance = randint(0, 1000)
                age = randint(18, 65)
                phone_number = f"090114010{i:02d}"

                # Alchemy PG insert
                sql_customer = Customer(
                    name=f"Customer {i}",
                    age=age,
                    city=city,
                    phone_number=phone_number,
                )
                session.add(sql_customer)
                await session.flush()


                sql_wallet = Wallet(in_to_wallet=balance, customer_id=sql_customer.id,phone_number=sql_customer.phone_number)
                session.add(sql_wallet)

                sql_scores_wallet = ScoresWallet(in_to_scores_wallet=10, phone_number=sql_customer.phone_number)
                session.add(sql_scores_wallet)

                await session.commit()

                customer = Customers(
                    id=str(sql_customer.id),
                    name=f"Customer {i}",
                    age=age,
                    city=city,
                    phone_number=str(phone_number),
                )

                # Save customer to Redis
                await redis.json().set(f"models.Customers:{customer.phone_number}", "$", customer.dict())
                scores_wallet = ScoresWallets(id=str(sql_scores_wallet.id), customer_id=str(sql_customer.id))
                await redis.json().set(f"models.ScoresWallets:{customer.phone_number}", "$", scores_wallet.dict())
                wallet = Wallets(id=str(sql_wallet.id), in_to_wallet=0, out_of_wallet=0, customer_id=str(sql_customer.id))
                await redis.json().set(f"models.Wallets:{customer.phone_number}", "$", wallet.dict())
                self.customers_id_list.append(customer.id)

    async def setup_salon_data(self, redis):
        async with async_session() as session:
            for i in range(1, 51):
                artists = [choice(self.artists_list) for _ in range(10)]
                services = [service for artist in artists for service in artist.services]
                city = choice(self.cities)
                age = randint(1, 20)

                # Alchemy PG insert
                sql_salon = Salon(name=f"salon {i}", age=age, city=city)
                for artist in artists:
                    sql_artist = await session.get(Artist, int(artist.id))
                    sql_salon.artists.append(sql_artist)
                for service in services:
                    sql_service = await session.get(Service, int(service.id))
                    sql_salon.services.append(sql_service)

                session.add(sql_salon)
                await session.flush()  # Ensure the salon is added and ID is generated
                salon_id = str(sql_salon.id)  # Get the generated id and assign it to the string id

                # Commit the salon data to the database
                await session.commit()

                # Now create the group for customers
                create_group_for_customers(sql_salon.id, "BaseGroup")

                salon = Salons(id=salon_id, name=f"Salon {i}", age=age, city=city, artists=artists, services=services)
                await redis.json().set(f"models.Salons:{salon.id}", "$", salon.dict())

    async def generate_sample_reserves(self, redis):
            time = datetime.now()

            for i in range(1, 11):
                reserve=Reserve(
                    id=i,
                    time=datetime.now().strftime("%Y-%m-%d %H:%M"),
                    time_jalali = jdatetime.datetime.fromgregorian(datetime=time).strftime("%Y-%m-%d %H:%M"),
                    start_stamp=5000000,
                    end_stamp= 3600,
                    available=False,
                    phone_number = f"090114010{i:02d}",
                    salon_id=i,
                    salon_name=f"Fater {i}",
                    artist_id=i,
                    artist_name=f"yaser {i}",
                    service_id=i,
                    service_name=f"ghater {i}",
                    reserved_at_datetime=datetime.now().strftime("%Y-%m-%d %H:%M"),
                    reserved_at_timestamp= 5000000000,
                    reserved_at_jalali= jdatetime.datetime.fromgregorian(datetime=time).strftime("%Y-%m-%d %H:%M"),
                    reserved_at= datetime.now().strftime("%Y-%m-%d %H:%M"),
                )

                await redis.json().set(f"models.Reserves:{i}", "$", reserve.dict())


    async def run(self):
            redis =  Redis(host='192.168.16.143', port=6290, db=0)
            start_time = datetime.now()
            await self.generate_services(redis)
            await self.generate_artists(redis)
            await self.setup_salon_data(redis)
            await self.generate_customers(redis)
            await self.generate_sample_reserves(redis)
            end_time = datetime.now() - start_time
            print(end_time)


async def main():
    generator = SalonDataGenerator()
    await generator.run()


if __name__ == "__main__":
    asyncio.run(main())