import os
import json
import logging
import pika
from pika.exceptions import AMQPError

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://rabbit_admin:rabbit_secret_q10@localhost:5672/")
EXCHANGE_NAME = os.getenv("RABBITMQ_ORDERS_EXCHANGE", "order_flow_exchange")
QUEUE_NAME = os.getenv("RABBITMQ_ORDER_CREATED_QUEUE", "order_created_queue")

def publish_order_created_event(event_data: dict) -> None:
    """
    Publica de forma síncrona y duradera un evento OrderCreated en RabbitMQ.
    Si el broker no está disponible, lanza una excepción para ser capturada en la capa HTTP
    y evitar inconsistencias transaccionales.
    """
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        params.socket_timeout = 3.0 # Timeout corto para no bloquear a los clientes web
        
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        # Aseguramos que la cola y el exchange existan y sean duraderos (no se pierden al reiniciar)
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key="order.created")

        payload = json.dumps(event_data)

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="order.created",
            body=payload,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Mensaje persistente en disco
                content_type='application/json'
            )
        )

        logger.info(f"[RabbitMQ] Evento OrderCreated publicado con éxito: {event_data['eventId']}")
        connection.close()

    except Exception as e:
        logger.error(f"[RabbitMQ] Fallo crítrice al conectar con el broker al publicar evento: {str(e)}")
        raise RuntimeError(f"Error de conexión con RabbitMQ: {str(e)}")
