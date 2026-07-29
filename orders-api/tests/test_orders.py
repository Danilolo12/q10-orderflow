import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import get_db, Base
from models import Stock, Order

# Utilizar SQLite en memoria para que los tests de Fase 2 corran ultrarrápido sin requerir Postgres local
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
    # Sembramos 1 producto en la BD de pruebas (Simula init-db.sql)
    db.add(Stock(sku="LAPTOP-PRO-16", name="MacBook Pro 16", available_quantity=10, price=3499.00))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

def test_health_check_fase2():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "orders-api"
    assert "Phase" or "Ready" in response.json()["phase"]

def test_create_order_success_pending():
    """
    Fase 2: Valida que al crear con un cliente válido, un SKU existente y cantidad 1-100,
    se registre inmediatamente en PostgreSQL en estado 'Pending'.
    """
    payload = {
        "customer_name": "Daniel Ramos (Cliente Senior)",
        "sku": "LAPTOP-PRO-16",
        "quantity": 3
    }
    response = client.post("/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_name"] == "Daniel Ramos (Cliente Senior)"
    assert data["sku"] == "LAPTOP-PRO-16"
    assert data["quantity"] == 3
    assert data["status"] == "Pending"

def test_validation_quantity_zero_or_negative_fails():
    payload = {"customer_name": "Daniel Ramos", "sku": "LAPTOP-PRO-16", "quantity": 0}
    response = client.post("/orders", json=payload)
    # Debe fallar por validación Pydantic con HTTP 422 Unprocessable Entity
    assert response.status_code == 422

def test_validation_quantity_exceeding_max_fails():
    payload = {"customer_name": "Daniel Ramos", "sku": "LAPTOP-PRO-16", "quantity": 101}
    response = client.post("/orders", json=payload)
    assert response.status_code == 422

def test_validation_empty_customer_name_fails():
    payload = {"customer_name": "    ", "sku": "LAPTOP-PRO-16", "quantity": 5}
    response = client.post("/orders", json=payload)
    assert response.status_code == 422

def test_create_order_non_existent_sku_in_seed():
    """
    Si el usuario manda un SKU que no figura en la tabla 'stock', el endpoint debe abortar con 404.
    """
    payload = {"customer_name": "Daniel Ramos", "sku": "SKU-INEXISTENTE", "quantity": 1}
    response = client.post("/orders", json=payload)
    assert response.status_code == 404
    assert "no existe en el seed" in response.json()["detail"]
