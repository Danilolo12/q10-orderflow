import pytest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import get_db, Base
from models import Stock, Order

# BD en memoria aislada para tests ágiles
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
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

def test_health_check_phase_3():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "orders-api"
    assert "Phase" or "RabbitMQ" in response.json()["phase"]

@patch("main.publish_order_created_event")
def test_create_order_success(mock_publisher):
    """
    Verifica creación exitosa en BD (Pending) y llamada a publicación en RabbitMQ de OrderCreated
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

def test_validation_quantity_low_fails():
    payload = {"customer_name": "Daniel Ramos", "sku": "TEST-LAPTOP", "quantity": 0}
    response = client.post("/orders", json=payload)
    assert response.status_code == 422

def test_validation_quantity_high_fails():
    payload = {"customer_name": "Daniel Ramos", "sku": "TEST-LAPTOP", "quantity": 101}
    response = client.post("/orders", json=payload)
    assert response.status_code == 422

def test_validation_empty_customer_name_fails():
    payload = {"customer_name": "   ", "sku": "TEST-LAPTOP", "quantity": 5}
    response = client.post("/orders", json=payload)
    assert response.status_code == 422

def test_create_order_non_existent_sku():
    payload = {"customer_name": "Daniel Ramos", "sku": "SKU-FANTASMA", "quantity": 5}
    response = client.post("/orders", json=payload)
    assert response.status_code == 404
    assert "no figura" in response.json()["detail"].lower() or "no existe" in response.json()["detail"].lower()

@patch("main.publish_order_created_event", side_effect=RuntimeError("RabbitMQ Broker Offline Simulated"))
def test_create_order_rabbitmq_failure_fallback(mock_publisher):
    """
    Lógica Crítica Exigida: Cuando RabbitMQ rechaza o falla en el publish de OrderCreated,
    la API debe capturar el error, marcar en BD como 'Failed - Broker Offline' y devolver un 500 claro al frontend.
    """
    payload = {"customer_name": "Daniel Ramos", "sku": "TEST-LAPTOP", "quantity": 1}
    response = client.post("/orders", json=payload)
    
    assert response.status_code == 500
    assert "rabbitmq" in response.json()["detail"].lower() or "broker" in response.json()["detail"].lower()

    # Comprobamos con la base de datos local del test que la transición a fallido ocurrió efectivamente
    db = TestingSessionLocal()
    order = db.query(Order).first()
    assert order is not None
    assert order.status == "Failed - Broker Offline"
    db.close()
