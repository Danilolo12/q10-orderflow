-- ==============================================================================
-- Q10 ORDERFLOW - SCRIPT DE INICIALIZACIÓN DE BASE DE DATOS Y SEEDING
-- Se ejecuta automáticamente al iniciar el contenedor de PostgreSQL
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

-- 2. Tabla de Pedidos / Orders
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) NOT NULL REFERENCES stock(sku) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity >= 1 AND quantity <= 100),
    status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla de Idempotencia para el Worker de Inventario
-- Evita procesamiento duplicado de eventos de RabbitMQ por re-intentos o redelivery
CREATE TABLE IF NOT EXISTS processed_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL DEFAULT 'OrderCreated',
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices de consulta para optimizar búsquedas por estado o por cliente
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);

-- ==============================================================================
-- SEEDING DE INVENTARIO INICIAL (Al menos 3 productos para la prueba)
-- ==============================================================================
INSERT INTO stock (sku, name, available_quantity, price) VALUES 
('LAPTOP-PRO-16', 'MacBook Pro 16" M4 Max Space Black', 10, 3499.00),
('PHONE-ULTRA-24', 'Samsung Galaxy S24 Ultra Titanium Black', 15, 1299.00),
('HEADPHONES-ANC', 'Sony WH-1000XM5 Wireless Headphones', 5, 399.00),
('KEYBOARD-MECH', 'Keychron Q1 Pro Wireless Mechanical', 25, 199.00)
ON CONFLICT (sku) DO UPDATE SET 
    available_quantity = EXCLUDED.available_quantity,
    name = EXCLUDED.name,
    price = EXCLUDED.price;
