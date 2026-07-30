import pytest
import json
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import get_db, Base
from models import Stock, Order
import rabbit_consumer

# BD en memoria aislada para tests ágiles de alta fidelidad
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override para inyección de dependencias en FastAPI
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Override para el consumidor asíncrono de RabbitMQ en Orders API
rabbit_consumer.SessionLocal = TestingSessionLocal

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.add(Stock(sku="TEST-LAPTOP", name="MacBook Test Pro", available_quantity=10, price=2999.00))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@patch("main.publish_order_created_event")
def test_01_create_order_pending_transition(mock_publisher):
    """
    1. TRANSICIÓN DE ESTADO (INICIAL) & CREACIÓN:
    Valida que un pedido válido con stock en catálogo se crea transaccionalmente en la base de datos
    bajo el estado inicial 'Pending' y emite correctamente el evento OrderCreated al broker RabbitMQ.
    """
    mock_publisher.return_value = None

    payload = {
        "customer_name": "Daniel Ramos",
        "sku": "TEST-LAPTOP",
        "quantity": 2
    }
    response = client.post("/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_name"] == "Daniel Ramos"
    assert data["sku"] == "TEST-LAPTOP"
    assert data["quantity"] == 2
    assert data["status"] == "Pending"
    mock_publisher.assert_called_once()


def test_02_order_validation_rules_and_not_found():
    """
    2. VALIDACIÓN DEL PEDIDO (REGLAS DE NEGOCIO Y CATÁLOGO):
    Valida en una suite integral que el API proteja la integridad transaccional rechazando:
    - Cantidad nula o negativa (<= 0) -> HTTP 422
    - Cantidad excesiva (> 100 por transacción) -> HTTP 422
    - Nombre de cliente vacío o con solo espacios en blanco -> HTTP 422
    - SKU inexistente en la tabla de productos de inventario -> HTTP 404
    """
    # Cantidad 0 o negativa
    resp_zero = client.post("/orders", json={"customer_name": "Daniel", "sku": "TEST-LAPTOP", "quantity": 0})
    assert resp_zero.status_code == 422

    # Cantidad mayor al límite transaccional de 100
    resp_high = client.post("/orders", json={"customer_name": "Daniel", "sku": "TEST-LAPTOP", "quantity": 101})
    assert resp_high.status_code == 422

    # Nombre de cliente vacío
    resp_empty = client.post("/orders", json={"customer_name": "   ", "sku": "TEST-LAPTOP", "quantity": 1})
    assert resp_empty.status_code == 422

    # SKU fantasma / inexistente
    resp_404 = client.post("/orders", json={"customer_name": "Daniel", "sku": "SKU-INEXISTENTE", "quantity": 1})
    assert resp_404.status_code == 404
    assert "no figura" in resp_404.json()["detail"].lower() or "no existe" in resp_404.json()["detail"].lower()


@patch("main.publish_order_created_event", side_effect=RuntimeError("RabbitMQ Broker Offline Simulated"))
def test_03_rabbitmq_broker_offline_fallback(mock_publisher):
    """
    3. MANEJO EXPLÍCITO DE FALLOS (BROKER CAÍDO):
    Lógica Crítica Exigida: Si el broker RabbitMQ está caído o rechaza la conexión al intentar publicar
    el evento, el sistema no deja el pedido en un limbo inconsistente. Captura la excepción transaccionalmente,
    transiciona el estado del pedido a 'Failed - Broker Offline' y retorna un HTTP 500 explicativo.
    """
    payload = {"customer_name": "Daniel Ramos", "sku": "TEST-LAPTOP", "quantity": 1}
    response = client.post("/orders", json=payload)
    
    assert response.status_code == 500
    assert "rabbitmq" in response.json()["detail"].lower() or "broker" in response.json()["detail"].lower()

    # Comprobar en base de datos la transición de resiliencia al estado de fallo
    db = TestingSessionLocal()
    order = db.query(Order).first()
    assert order is not None
    assert order.status == "Failed - Broker Offline"
    db.close()


@patch("main.publish_order_created_event")
def test_04_status_consumer_transitions_confirmed_and_rejected(mock_publisher):
    """
    4. TRANSICIONES DE ESTADO (CONFIRMACIÓN Y RECHAZO DESDE INVENTORY WORKER):
    Valida la lógica crítica de sincronización asíncrona: cuando el consumidor en orders-api recibe
    los eventos de respuesta del worker de inventario por la cola 'order_status_queue', realiza
    las transiciones de estado de 'Pending' hacia 'Confirmed' (stock descontado) o 'Rejected' (sin stock).
    """
    mock_publisher.return_value = None

    # 1. Crear pedido A para ser confirmado
    res_a = client.post("/orders", json={"customer_name": "Cliente A", "sku": "TEST-LAPTOP", "quantity": 2})
    order_id_a = res_a.json()["id"]

    # 2. Crear pedido B para ser rechazado por falta de stock posterior
    res_b = client.post("/orders", json={"customer_name": "Cliente B", "sku": "TEST-LAPTOP", "quantity": 5})
    order_id_b = res_b.json()["id"]

    ch_mock = MagicMock()
    method_mock = MagicMock(delivery_tag=1)

    # Simular llegada del mensaje StockConfirmed para Pedido A
    event_confirmed = json.dumps({
        "eventId": str(uuid.uuid4()),
        "orderId": order_id_a,
        "status": "Confirmed",
        "reason": "Stock reservado exitosamente"
    })
    rabbit_consumer.status_consumer._process_message(ch_mock, method_mock, None, event_confirmed)
    ch_mock.basic_ack.assert_called_with(delivery_tag=1)

    # Simular llegada del mensaje StockRejected para Pedido B
    method_mock.delivery_tag = 2
    event_rejected = json.dumps({
        "eventId": str(uuid.uuid4()),
        "orderId": order_id_b,
        "status": "Rejected",
        "reason": "Stock insuficiente"
    })
    rabbit_consumer.status_consumer._process_message(ch_mock, method_mock, None, event_rejected)

    # Verificar en base de datos que las transiciones ocurrieron correctamente
    db = TestingSessionLocal()
    o_a = db.query(Order).filter(Order.id == uuid.UUID(order_id_a)).first()
    o_b = db.query(Order).filter(Order.id == uuid.UUID(order_id_b)).first()
    assert o_a.status == "Confirmed"
    assert o_b.status == "Rejected"
    db.close()


@patch("main.publish_order_created_event")
def test_05_consumer_idempotency_duplicate_status_events(mock_publisher):
    """
    5. IDEMPOTENCIA DEL CONSUMIDOR (MENSAJES DUPLICADOS POR REINTENTOS DE RED):
    Valida que ante reintentos de entrega (at-least-once delivery) donde el mismo mensaje de confirmación
    llega múltiples veces a la API, el sistema procesa de forma totalmente idempotente, reconociendo (ACK)
    el mensaje sin generar excepciones ni alterar o corromper el estado final del pedido.
    (Nota: La idempotencia con bloqueo pesimista contra doble descuento de stock se valida en inventory-worker).
    """
    mock_publisher.return_value = None
    res = client.post("/orders", json={"customer_name": "Cliente Idemp", "sku": "TEST-LAPTOP", "quantity": 1})
    order_id = res.json()["id"]

    ch_mock = MagicMock()
    method_mock = MagicMock(delivery_tag=10)

    payload_confirmed = json.dumps({
        "eventId": str(uuid.uuid4()),
        "orderId": order_id,
        "status": "Confirmed",
        "reason": "Stock reservado exitosamente"
    })

    # Primera llegada
    rabbit_consumer.status_consumer._process_message(ch_mock, method_mock, None, payload_confirmed)
    db1 = TestingSessionLocal()
    assert db1.query(Order).filter(Order.id == uuid.UUID(order_id)).first().status == "Confirmed"
    db1.close()

    # Segunda llegada (duplicado idéntico redelivery por RabbitMQ)
    method_mock.delivery_tag = 11
    rabbit_consumer.status_consumer._process_message(ch_mock, method_mock, None, payload_confirmed)
    ch_mock.basic_ack.assert_called_with(delivery_tag=11)

    db2 = TestingSessionLocal()
    assert db2.query(Order).filter(Order.id == uuid.UUID(order_id)).first().status == "Confirmed"
    db2.close()
