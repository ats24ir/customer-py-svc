import pika
import json


connection = pika.BlockingConnection(pika.ConnectionParameters(
    host='192.168.16.143',
    port=5673,
    credentials=pika.PlainCredentials('guest', 'guest')  # Credentials
))
channel = connection.channel()


exchange_name = 'auth_exchange'


def send_jwt_request(phone_number):

    message = json.dumps({"phone_number": phone_number})


    headers = {'task_type': 'generate_access_token'}
    priority = 1


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
    print(f"Sent JWT request for phone number: {phone_number}")


if __name__ == '__main__':
    phone_number = "09011462424"
    send_jwt_request(phone_number)
    connection.close()