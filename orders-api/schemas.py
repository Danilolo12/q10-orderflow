from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator

# ==============================================================================
# SCHEMAS PARA PRODUCTOS / INVENTARIO
# ==============================================================================
class ProductResponse(BaseModel):
    sku: str
    name: str
    available_quantity: int
    price: Decimal

    class Config:
        from_attributes = True

# ==============================================================================
# SCHEMAS PARA PEDIDOS (ORDERS)
# ==============================================================================
class OrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=150, description="Nombre completo del cliente (No vacío)")
    sku: str = Field(..., min_length=2, max_length=100, description="SKU identificador del producto en catálogo")
    quantity: int = Field(..., ge=1, le=100, description="Cantidad solicitada (1 a 100 unidades por pedido)")

    @field_validator("customer_name", "sku")
    def strip_whitespace(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Este campo no puede estar vacío o consistir únicamente en espacios")
        return trimmed

class OrderResponse(BaseModel):
    id: UUID
    customer_name: str
    sku: str
    quantity: int
    status: str
    created_at: datetime
    updated_at: datetime
    product: Optional[ProductResponse] = None

    class Config:
        from_attributes = True
