import uuid
import logging
from datetime import datetime, timezone
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db, engine, Base, SessionLocal
from models import Order, Stock
from schemas import OrderCreate, OrderResponse, ProductResponse
from rabbit_publisher import publish_order_created_event
from rabbit_consumer import status_consumer
from seed import seed_products

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [OrdersAPI] - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Asegurar tablas en la base de datos de persistencia
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: Cargar catálogo de productos desde seed-data/products.json
    db = SessionLocal()
    seed_products(db)
    db.close()
    # Arrancar hilo secundario para escuchar eventos StockReserved / StockRejected desde RabbitMQ
    logger.info("[Lifespan] Conectando consumidor secundario a RabbitMQ para transiciones de estado...")
    status_consumer.start()
    yield
    # SHUTDOWN: Detener el hilo limpiamente tras apagar el servicio
    logger.info("[Lifespan] Apagando conector de colas de Orders API...")
    status_consumer.stop()

app = FastAPI(
    title="Q10 OrderFlow - Orders API (Fase 3 Core)",
    description="Microservicio REST de Pedidos integrado de punta a punta con RabbitMQ y PostgreSQL",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", summary="Healthcheck del servicio Orders API")
def health_check():
    return {"status": "UP", "service": "orders-api", "phase": "3 - RabbitMQ Messaging Core Active"}

@app.get("/products", response_model=List[ProductResponse], summary="Consultar inventario en PostgreSQL")
def list_products(db: Session = Depends(get_db)):
    return db.query(Stock).order_by(Stock.name.asc()).all()

@app.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido y emitir evento OrderCreated a RabbitMQ"
)
def create_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    """
    LÓGICA SENIOR FASE 3 (REST + Mensajería Asíncrona Resiliente):
    1. Valida el contrato Pydantic (cliente no vacío, cantidad entre 1 y 100).
    2. Comprueba existencia real del SKU en catálogo de stock.
    3. Persiste inicialmente el pedido en PostgreSQL con estado 'Pending'.
    4. Genera un eventId UUID único y publica un evento 'OrderCreated' hacia RabbitMQ.
    5. MANEJO DE FALLOS CRITICO: Si el broker RabbitMQ no responde al intentar publicar,
       se captura la excepción, se marca el pedido como 'Failed - Broker Offline' en BD,
       y se informa del error al usuario mediante un código HTTP 500 explícito.
    """
    # 1. Verificar existencia obligatoria del producto
    product = db.query(Stock).filter(Stock.sku == order_in.sku).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El SKU '{order_in.sku}' no figura en nuestro catálogo oficial del sistema."
        )

    # 2. Registrar de forma transaccional el pedido en estado Pending
    new_order = Order(
        id=uuid.uuid4(),
        customer_name=order_in.customer_name,
        sku=order_in.sku,
        quantity=order_in.quantity,
        status="Pending"
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 3. Empujar la notificación asíncrona hacia RabbitMQ con ID de evento inmutable
    event_id = str(uuid.uuid4())
    event_payload = {
        "eventId": event_id,
        "eventType": "OrderCreated",
        "orderId": str(new_order.id),
        "sku": new_order.sku,
        "quantity": new_order.quantity,
        "customerName": new_order.customer_name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # 4. Fallback y tolerancia a caídas en RabbitMQ (Exigido en enunciado de evaluación)
    try:
        publish_order_created_event(event_payload)
    except Exception as e:
        logger.error(f"[Broker Fallout] Error al contactar a RabbitMQ durante el pedido {new_order.id}. Revocando.")
        new_order.status = "Failed - Broker Offline"
        db.commit()
        db.refresh(new_order)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error crítico en el broker de mensajería (RabbitMQ Inalcanzable). Pedido cancelado transaccionado a fallido por seguridad."
        )

    return new_order

@app.get("/orders", response_model=List[OrderResponse], summary="Historial general de pedidos para Live Polling")
def get_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(desc(Order.created_at)).all()

@app.get("/orders/{order_id}", response_model=OrderResponse, summary="Detalle individual de pedido")
def get_order(order_id: uuid.UUID, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No se encontró un pedido registrado para el UUID {order_id}")
    return order
