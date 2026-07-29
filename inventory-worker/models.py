import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Numeric, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Stock(Base):
    """
    Modelo de Stock en Inventario.
    Se utiliza bloqueo pesimista en las transacciones (FOR UPDATE) para restar cantidades con seguridad.
    """
    __tablename__ = "stock"

    sku = Column(String(100), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    available_quantity = Column(Integer, CheckConstraint("available_quantity >= 0"), nullable=False, default=0)
    price = Column(Numeric(10, 2), nullable=False, default=0.0)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class ProcessedEvent(Base):
    """
    Tabla obligatoria de IDEMPOTENCIA (processed_events).
    Asegura que un mismo event_id de RabbitMQ jamás descuente saldo por partida doble
    en caso de re-intentos de red.
    """
    __tablename__ = "processed_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True)
    event_type = Column(String(100), nullable=False, default="OrderCreated")
    processed_at = Column(DateTime(timezone=True), default=utc_now)
