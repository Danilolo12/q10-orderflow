import os
import json
import time
import logging
import threading
import pika
from pika.exceptions import AMQPConnectionError
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Order

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://rabbit_admin:rabbit_secret_q10@localhost:5672/")
STATUS_QUEUE = os.getenv("RABBITMQ_ORDER_STATUS_QUEUE", "order_status_queue")
EXCHANGE_NAME = os.getenv("RABBITMQ_ORDERS_EXCHANGE", "order_flow_exchange")

class RabbitMQStatusConsumer:
    """
    Consumidor que ejecuta en un hilo secundario en Orders API.
    Escucha eventos de respuesta del worker de inventario (StockReserved, StockRejected)
    y actualiza de forma automática la base de datos de los pedidos.
    """
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="OrderStatusConsumerThread")
        self._thread.start()
        logger.info("[Consumer] Hilo de escucha de estados iniciado.")

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logger.info("[Consumer] Hilo de escucha de estados detenido.")

    def _process_message(self, ch, method, properties, body):
        try:
            data = json.loads(body)
            order_id = data.get("orderId")
            status = data.get("status")  # "Confirmed" o "Rejected"
            reason = data.get("reason", "")

            if not order_id or not status:
                logger.warning(f"[Consumer] Mensaje con formato inválido ignorado: {body}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            db: Session = SessionLocal()
            try:
                order = db.query(Order).filter(Order.id == order_id).first()
                if order:
                    old_status = order.status
                    order.status = status
                    db.commit()
                    logger.info(f"[Consumer] Pedido {order_id} actualizado: {old_status} -> {status} ({reason})")
                else:
                    logger.warning(f"[Consumer] Pedido no encontrado en BD para ID: {order_id}")
            except Exception as ex:
                db.rollback()
                logger.error(f"[Consumer] Error al actualizar la base de datos: {ex}")
                # Rechazar sin requeue si es un error de datos fatal, o requeue si es un intermitente
            finally:
                db.close()

            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"[Consumer] Error inesperado al procesar mensaje: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                params = pika.URLParameters(RABBITMQ_URL)
                params.heartbeat = 60
                connection = pika.BlockingConnection(params)
                channel = connection.channel()

                channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
                channel.queue_declare(queue=STATUS_QUEUE, durable=True)
                channel.queue_bind(exchange=EXCHANGE_NAME, queue=STATUS_QUEUE, routing_key="order.status")

                channel.basic_qos(prefetch_count=10)
                channel.basic_consume(queue=STATUS_QUEUE, on_message_callback=self._process_message)

                logger.info(f"[Consumer] Conectado a RabbitMQ. Escuchando cola '{STATUS_QUEUE}'...")
                while not self._stop_event.is_set() and connection.is_open:
                    connection.process_data_events(time_limit=1)
                
                if connection.is_open:
                    connection.close()

            except (AMQPConnectionError, Exception) as e:
                if not self._stop_event.is_set():
                    logger.warning(f"[Consumer] Desconexión o error en RabbitMQ ({e}). Re-intentando en 5s...")
                    time.sleep(5)

# Singleton consumidor
status_consumer = RabbitMQStatusConsumer()
