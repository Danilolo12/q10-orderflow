import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Stock(Base):
    """
    Modelo de Inventario (Tabla stock).
    Se lee desde Orders API para consultar qué productos existen y exhibir en el frontend.
    """
    __tablename__ = "stock"

    sku = Column(String(100), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    available_quantity = Column(Integer, CheckConstraint("available_quantity >= 0"), nullable=False, default=0)
    price = Column(Numeric(10, 2), nullable=False, default=0.0)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    orders = relationship("Order", back_populates="product")

class Order(Base):
    """
    Modelo de Pedido (Tabla orders).
    Representa el estado del flujo del pedido (Pending -> Confirmed / Rejected / Failed).
    """
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_name = Column(String(255), nullable=False)
    sku = Column(String(100), ForeignKey("stock.sku", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, CheckConstraint("quantity >= 1 AND quantity <= 100"), nullable=False)
    status = Column(String(50), nullable=False, default="Pending")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    product = relationship("Stock", back_populates="orders")
