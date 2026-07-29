-- ==============================================================================
-- Q10 ORDERFLOW - ESQUEMA DE BASE DE DATOS
-- Se ejecuta automáticamente al iniciar el contenedor de PostgreSQL.
-- Los datos de productos se cargan desde seed-data/products.json al arrancar la API.
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Tabla de Inventario / Productos
CREATE TABLE IF NOT EXISTS stock (
    sku VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    available_quantity INTEGER NOT NULL CHECK (available_quantity >= 0),
    price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Pedidos
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) NOT NULL REFERENCES stock(sku) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity >= 1 AND quantity <= 100),
    status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla de Idempotencia para el Inventory Worker
CREATE TABLE IF NOT EXISTS processed_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL DEFAULT 'OrderCreated',
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices de consulta
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
