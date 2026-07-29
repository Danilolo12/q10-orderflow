import uuid
import logging
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db, engine, Base
from models import Order, Stock
from schemas import OrderCreate, OrderResponse, ProductResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [OrdersAPI-Fase2] - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Aseguramos que los metadatos relacionales estén empatados en PostgreSQL
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Q10 OrderFlow - Orders API (Fase 2)",
    description="Microservicio REST de Pedidos con validación Pydantic estricta y persistencia en PostgreSQL (SQLAlchemy)",
    version="2.0.0"
)

# Middleware para que nuestro futuro Frontend React (Puerto 5173) no tenga restricciones CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", summary="Healthcheck del contenedor para Docker Compose")
def health_check():
    return {"status": "UP", "service": "orders-api", "phase": "2 - Database & Validations Ready"}

@app.get("/products", response_model=List[ProductResponse], summary="Listado auxiliar de productos para el Frontend")
def list_products(db: Session = Depends(get_db)):
    """
    Retorna el catálogo y su stock en PostgreSQL (los 4 productos seedeados por init-db.sql)
    para alimentar el menú desplegable en React en la Fase 4.
    """
    return db.query(Stock).order_by(Stock.name.asc()).all()

@app.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo pedido con validación de SKU y estado 'Pending'"
)
def create_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    """
    LÓGICA SENIOR FASE 2 (Validación + Persistencia sin Broker aún):
    1. Pydantic ya validó que customer_name (clienteNombre) no sea una cadena vacía ni espacios.
    2. Pydantic ya garantizó matemáticamente que quantity sea entre 1 y 100.
    3. Consultamos la tabla 'stock' en PostgreSQL para verificar que el SKU provisto exista
       realmente entre los productos iniciales de seed.
    4. Grabamos en base de datos con estado inalterable 'Pending' y retornamos el registro de inmediato.
    
    * Nota arquitectónica: En la Fase 3 integraremos aquí la emisión asincrónica a RabbitMQ.
    """
    # Verificación estricta de que el SKU existe realmente en el almacén (seed inicial)
    product = db.query(Stock).filter(Stock.sku == order_in.sku).first()
    if not product:
        logger.warning(f"Intento de crear pedido con SKU inasumible: {order_in.sku}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error de catálogo: El producto con SKU '{order_in.sku}' no existe en el seed inicial."
        )

    # Creación y persistencia transaccional del pedido
    new_order = Order(
        id=uuid.uuid4(),
        customer_name=order_in.customer_name,
        sku=order_in.sku,
        quantity=order_in.quantity,
        status="Pending"
    )
    
    try:
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        logger.info(f"[Fase 2 Exito] Pedido encolado localmente en DB (Pending). ID: {new_order.id}")
        # TODO [Fase 3]: Aquí enviaremos el evento OrderCreated hacia las colas de RabbitMQ.
    except Exception as ex:
        db.rollback()
        logger.error(f"Fallo grave en inserción SQLAlchemy: {ex}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo de transacción SQL en PostgreSQL")

    return new_order

@app.get("/orders", response_model=List[OrderResponse], summary="Consultar historial general de pedidos")
def get_orders(db: Session = Depends(get_db)):
    """
    Lista todos los pedidos registrados en PostgreSQL ordenados cronológicamente
    de más recientes a antiguos (esencial para hacer polling fluido desde React en la Fase 4).
    """
    return db.query(Order).order_by(desc(Order.created_at)).all()

@app.get("/orders/{order_id}", response_model=OrderResponse, summary="Consultar detalle de un pedido por su UUID")
def get_order(order_id: uuid.UUID, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe ningún registro para el ID de pedido {order_id}"
        )
    return order
