import pika
import json
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

connection = pika.BlockingConnection(pika.ConnectionParameters(
    host='192.168.16.143',
    port=5673,
    credentials=pika.PlainCredentials('guest', 'guest')
))
channel = connection.channel()

exchange_name = 'auth_exchange'


def send_phone_number(phone_number):
    message = json.dumps({"phone_number": phone_number})
    headers = {'task_type': 'generate_otp'}
    priority = 9


    channel.basic_publish(
        exchange=exchange_name,
        routing_key='',
        body=message,
        properties=pika.BasicProperties(
            headers=headers,
            priority=priority,
            delivery_mode=2
        )
    )
    logging.info(f"Sent phone number: {phone_number}")

for i in range(1000):
    if __name__ == '__main__':
        phone_number = i
        send_phone_number(phone_number)
        # connection.close()
        logging.info("Message sent successfully, closing connection")