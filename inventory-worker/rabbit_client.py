import os
import json
import logging
import pika
from pika.exceptions import AMQPError

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://rabbit_admin:rabbit_secret_q10@localhost:5672/")
EXCHANGE_NAME = os.getenv("RABBITMQ_ORDERS_EXCHANGE", "order_flow_exchange")
STATUS_QUEUE = os.getenv("RABBITMQ_ORDER_STATUS_QUEUE", "order_status_queue")

def publish_stock_response(event_id: str, order_id: str, status: str, reason: str = "", channel=None):
    """
    Publica el resultado de la reserva (StockReserved o StockRejected) hacia Orders API.
    Reutiliza el canal del consumidor si está disponible para máxima velocidad.
    """
    payload = {
        "eventId": event_id,
        "orderId": order_id,
        "status": status,
        "reason": reason
    }
    
    should_close_conn = False
    if channel is None or not channel.is_open:
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        should_close_conn = True

    try:
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
        channel.queue_declare(queue=STATUS_QUEUE, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=STATUS_QUEUE, routing_key="order.status")

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="order.status",
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json'
            )
        )
        logger.info(f"[Worker Publisher] Publicado evento hacia orders: {status} para Pedido {order_id}")
    finally:
        if should_close_conn:
            channel.connection.close()
