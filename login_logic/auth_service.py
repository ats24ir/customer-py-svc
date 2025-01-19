import os
from dotenv import load_dotenv
import json
import logging
import jwt
import datetime
import time
import aio_pika
import asyncio
from random import randint
from customer_create import customer_get_or_create
from database_models.databases_connections import get_async_session, redis as r

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'env', '.env'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

SECRET_KEY = os.getenv('JWT_SECRET_KEY')
ACCESS_TOKEN_LIFETIME = datetime.timedelta(days=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_DAYS', 180)))

async def retry_async(coroutine, max_retries=3, delay=2, *args, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            return await coroutine(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries:
                logging.warning(f"Retry {attempt}/{max_retries} for {coroutine.__name__} failed: {str(e)}. Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logging.error(f"All retries for {coroutine.__name__} failed: {str(e)}")
                raise

async def generate_otp(phone_number, otp_expire):
    try:
        if await r.json().get(f"models.OTP:{phone_number}"):
            return
        logging.info(f"Generating OTP for phone number: {phone_number}")
        otp = randint(100000, 999999)
        otp_expire = int(otp_expire)
        otp_data = {"OTP": otp, "otp_expire": otp_expire, "time_stamp": time.time()}
        await r.json().set(f"models.OTP:{phone_number}", "$", otp_data)
        await r.expireat(f"models.OTP:{phone_number}", otp_expire)
        logging.info(f"Generated OTP {otp} for phone number {phone_number}")
    except Exception as e:
        logging.error(f"Error processing OTP: {str(e)}")
        raise

async def generate_access_token(phone_number, session_id, os, browser, device):
    async with get_async_session() as pgsession:
        try:
            now = datetime.datetime.now()
            await customer_get_or_create(phone_number, pgsession, r)
            access_payload = {
                "phone_number": phone_number,
                "type": "access",
                "exp": now + ACCESS_TOKEN_LIFETIME,
                "iat": now,
            }

            access_token = jwt.encode(access_payload, SECRET_KEY, algorithm="HS256")
            session = {
                "token": access_token,
                "device": device,
                "browser": browser,
                "os": os,
                "sessionId": session_id,
                "phoneNumber": phone_number
            }

            await r.json().set(f"models.Sessions:{session_id}", "$", session)
            await r.expire(f"models.Sessions:{session_id}", 15552000)

            await pgsession.commit()
            if not await r.json().get(f"models.Customers:{phone_number}") or \
                    not await r.json().get(f"models.ScoresWallets:{phone_number}") or \
                    not await r.json().get(f"models.Wallets:{phone_number}"):
                await pgsession.rollback()
                raise
            return access_token

        except Exception as e:
            logging.error(f"Error processing access token: {str(e)}")
            await pgsession.rollback()
            raise

async def consume_messages():
    connection = await aio_pika.connect_robust(
        f"amqp://{os.getenv('RABBITMQ_USER')}:{os.getenv('RABBITMQ_PASSWORD')}@{os.getenv('RABBITMQ_HOST')}:{os.getenv('RABBITMQ_PORT')}/"
    )
    channel = await connection.channel()

    await channel.declare_exchange('auth_exchange', type='direct', durable=True)
    await channel.declare_exchange('auth_dlx', type='direct', durable=True)

    dlq = await channel.declare_queue('auth_dlq', durable=True, arguments={'x-max-priority': 10})
    await dlq.bind('auth_dlx', routing_key='')

    queue = await channel.declare_queue('auth_queue', durable=True, arguments={
        'x-max-priority': 10,
        'x-dead-letter-exchange': 'auth_dlx',
        'x-dead-letter-routing-key': ''
    })
    await queue.bind('auth_exchange', routing_key='')

    async def callback(message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                logging.info(f"Received message with headers: {message.headers}")
                headers = message.headers
                task_type = headers['task_type']

                if task_type == 'generate_otp':
                    message_json = json.loads(message.body.decode())
                    phone_number = message_json["phoneNumber"]
                    otp_expire = message_json["otpExpire"]
                    if phone_number:
                        await retry_async(generate_otp, 3, 2, phone_number, otp_expire)
                        logging.info(f"Forwarded OTP request for phone number: {phone_number}")
                    else:
                        logging.error("Missing 'phone_number' in message body for OTP generation")
                elif task_type == 'generate_access_token':
                    message_json = json.loads(message.body.decode())
                    phone_number = message_json['phoneNumber']
                    session_id = message_json['sessionId']
                    browser = message_json['browser']
                    device = message_json['device']
                    os = message_json['os']

                    if phone_number:
                        await retry_async(generate_access_token, 3, 2, phone_number, session_id, os, browser, device)
                        logging.info(f"Forwarded JWT request for phone number: {phone_number}")
                        await channel.default_exchange.publish(
                            aio_pika.Message(
                                body=str(session_id).encode(),
                                headers={"correlationId": message.correlation_id}
                            ),
                            routing_key=message.reply_to
                        )
                    else:
                        logging.error("Missing 'phone_number' in message body for access token generation")
                else:
                    logging.error(f"Invalid task type in headers: {task_type}")

            except Exception as e:
                logging.error(f"Error processing message: {str(e)}")
                await message.nack(requeue=False)

    await queue.consume(callback)
    logging.info("Waiting for messages. To exit press CTRL+C")

    await asyncio.Future()

async def main():
    await consume_messages()

if __name__ == '__main__':
    asyncio.run(main())

