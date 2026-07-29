import os
import json
import logging
import pika

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://rabbit_admin:rabbit_secret_q10@localhost:5672/")
EXCHANGE_NAME = os.getenv("RABBITMQ_ORDERS_EXCHANGE", "order_flow_exchange")
STATUS_QUEUE = os.getenv("RABBITMQ_ORDER_STATUS_QUEUE", "order_status_queue")

def publish_stock_response(event_id: str, order_id: str, status: str, reason: str = "", channel=None):
    """
    Publica el resultado de la reserva (Confirmed o Rejected) hacia Orders API.
    SIEMPRE abre una conexión nueva e independiente para evitar conflictos
    con el canal consumidor que está en modo básico de lectura.
    """
    payload = {
        "eventId": event_id,
        "orderId": order_id,
        "status": status,
        "reason": reason
    }

    # Conexión dedicada para publicación — nunca reutilizar el canal consumidor
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        params.socket_timeout = 5.0
        connection = pika.BlockingConnection(params)
        pub_channel = connection.channel()

        pub_channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
        pub_channel.queue_declare(queue=STATUS_QUEUE, durable=True)
        pub_channel.queue_bind(exchange=EXCHANGE_NAME, queue=STATUS_QUEUE, routing_key="order.status")

        pub_channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="order.status",
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json'
            )
        )
        logger.info(f"[Publisher] Respuesta enviada -> {status} para Pedido {order_id}")
        connection.close()
    except Exception as e:
        logger.error(f"[Publisher] Error al publicar respuesta de stock: {e}")
