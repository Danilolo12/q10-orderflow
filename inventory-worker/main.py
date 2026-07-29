import os
import json
import time
import logging
import uuid
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy import select

import pika
from database import get_db_session, engine, Base
from models import Stock, ProcessedEvent
from rabbit_client import publish_stock_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [InventoryWorker] - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Garantizar tablas inicializadas
Base.metadata.create_all(bind=engine)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://rabbit_admin:rabbit_secret_q10@localhost:5672/")
EXCHANGE_NAME = os.getenv("RABBITMQ_ORDERS_EXCHANGE", "order_flow_exchange")
ORDERS_QUEUE = os.getenv("RABBITMQ_ORDER_CREATED_QUEUE", "order_created_queue")

def process_order_created(ch, method, properties, body):
    """
    LÓGICA SENIOR E IDEMPOTENTE:
    1. Lee el evento OrderCreated.
    2. Intenta registrar el eventId en 'processed_events' en la BD. Si falla por Primary Key (IntegrityError),
       el mensaje es duplicado (idempotencia cumplida); se ignora en silencio y se envía el ACK.
    3. Si el evento es nuevo: busca el stock utilizando .with_for_update() (Bloqueo pesimista de fila).
    4. Valida saldo suficiente:
       - Si alcanza: descuenta, commitea la transacción de BD, y emite 'StockReserved' -> Confirmed.
       - Si falta stock: hace rollback / guarda solo el evento procesado, y emite 'StockRejected' -> Rejected.
    """
    db = get_db_session()
    try:
        data = json.loads(body)
        event_id = data.get("eventId")
        order_id = data.get("orderId")
        sku = data.get("sku")
        quantity = data.get("quantity", 1)

        logger.info(f"==> Recibido OrderCreated. Evento: {event_id} | Order: {order_id} | SKU: {sku} x {quantity}")

        if not event_id or not order_id or not sku:
            logger.error("Mensaje inválido recibido. Descartando sin requeue.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            db.close()
            return

        event_uuid = uuid.UUID(str(event_id))

        # ======================================================================
        # PASO 1: VALIDACIÓN DE IDEMPOTENCIA
        # ======================================================================
        existing_event = db.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_uuid).first()
        if existing_event:
            logger.warning(f"[IDEMPOTENCIA] El Evento {event_id} ya se procesó previamente. Descartando silenciosamente.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            db.close()
            return

        # Intentar insertar registro en tabla de idempotencia dentro de una transacción soberana
        try:
            processed_record = ProcessedEvent(event_id=event_uuid, event_type="OrderCreated")
            db.add(processed_record)
            db.flush() # Forza verificación de PK duplicada sin commitear aún todo el bloque
        except IntegrityError:
            db.rollback()
            logger.warning(f"[IDEMPOTENCIA EXCEPCIÓN] Llave duplicada al insertar Evento {event_id}. Ignorando.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            db.close()
            return

        # ======================================================================
        # PASO 2: LÓGICA TRANSACCIONAL DE STOCK CON BLOQUEO DE FILA
        # ======================================================================
        # Bloquear fila de inventario para este SKU contra condiciones de carrera concurrentes
        stock_item = db.query(Stock).filter(Stock.sku == sku).with_for_update().first()

        if not stock_item:
            logger.error(f"SKU {sku} no existe en almacén. Rechazando pedido.")
            db.commit() # Guardamos evento como procesado para no repetir este error
            publish_stock_response(event_id, order_id, status="Rejected", reason="SKU inexistente en almacén", channel=ch)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            db.close()
            return

        if stock_item.available_quantity >= quantity:
            # STOCK SUFICIENTE: Restar, confirmar transacción y notificar éxito
            stock_item.available_quantity -= quantity
            db.commit()
            logger.info(f"[EXPLICIT EXCELLENCE] Stock reservado para {sku} (Nuevo saldo: {stock_item.available_quantity}).")
            
            publish_stock_response(event_id, order_id, status="Confirmed", reason="Stock disponible y reservado", channel=ch)
        else:
            # STOCK INSUFICIENTE: Mantener registro del evento, pero no tocar el saldo y emitir rechazo
            db.commit()
            reason_msg = f"Stock insuficiente (Disponible: {stock_item.available_quantity}, Solicitado: {quantity})"
            logger.warning(f"[SIN STOCK] {reason_msg} para Pedido {order_id}")
            
            publish_stock_response(event_id, order_id, status="Rejected", reason=reason_msg, channel=ch)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        db.rollback()
        logger.error(f"[Error no controlado] Fallo procesando mensaje {event_id}: {str(e)}")
        # Si es un error transitorio de conexión o DB, nack para re-intento posterior
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    finally:
        db.close()

def run_worker_loop():
    logger.info("=== Arrancando loop del Inventory Worker ===")
    while True:
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            params.heartbeat = 60
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
            channel.queue_declare(queue=ORDERS_QUEUE, durable=True)
            channel.queue_bind(exchange=EXCHANGE_NAME, queue=ORDERS_QUEUE, routing_key="order.created")

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=ORDERS_QUEUE, on_message_callback=process_order_created)

            logger.info(f"[Worker Ready] Escuchando activamente en cola '{ORDERS_QUEUE}'...")
            channel.start_consuming()

        except Exception as e:
            logger.warning(f"[Desconectado] Error en el canal del worker: {e}. Reconectando en 5 segundos...")
            time.sleep(5)

if __name__ == "__main__":
    run_worker_loop()
