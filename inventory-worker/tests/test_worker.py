import pytest
import json
import uuid
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db_session
from models import Stock, ProcessedEvent
import main

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db_session():
    return TestingSessionLocal()

main.get_db_session = override_get_db_session

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.add(Stock(sku="LAPTOP-PRO-16", name="MacBook Pro 16", available_quantity=10, price=3499.00))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

@patch("main.publish_stock_response")
def test_process_order_success(mock_publish):
    """
    Verifica que al recibir un pedido válido con saldo suficiente, se descuenta el stock
    y se emite una confirmación (Confirmed).
    """
    ch = MagicMock()
    method = MagicMock(delivery_tag=1)
    properties = MagicMock()
    
    event_id = str(uuid.uuid4())
    order_id = str(uuid.uuid4())
    payload = {
        "eventId": event_id,
        "orderId": order_id,
        "sku": "LAPTOP-PRO-16",
        "quantity": 3
    }
    
    main.process_order_created(ch, method, properties, json.dumps(payload))
    
    # Verificar ACK
    ch.basic_ack.assert_called_once_with(delivery_tag=1)
    
    # Verificar que el stock se descontó de 10 a 7
    db = TestingSessionLocal()
    stock = db.query(Stock).filter(Stock.sku == "LAPTOP-PRO-16").first()
    assert stock.available_quantity == 7
    
    # Verificar que se registró la idempotencia
    ev = db.query(ProcessedEvent).filter(ProcessedEvent.event_id == uuid.UUID(event_id)).first()
    assert ev is not None
    db.close()

    # Verificar publicación de respuesta Confirmed
    mock_publish.assert_called_once()
    assert mock_publish.call_args[1]["status"] == "Confirmed"

@patch("main.publish_stock_response")
def test_process_order_idempotency_duplicate_event(mock_publish):
    """
    PRUEBA CRÍTICA DE IDEMPOTENCIA:
    Si el mismo evento llega dos veces seguidas, la segunda vez debe ignorarse en silencio
    y NO descontar stock nuevamente.
    """
    ch = MagicMock()
    method = MagicMock(delivery_tag=2)
    properties = MagicMock()
    
    event_id = str(uuid.uuid4())
    order_id = str(uuid.uuid4())
    payload = {
        "eventId": event_id,
        "orderId": order_id,
        "sku": "LAPTOP-PRO-16",
        "quantity": 2
    }
    
    # Primera entrega del mensaje
    main.process_order_created(ch, method, properties, json.dumps(payload))
    
    db = TestingSessionLocal()
    assert db.query(Stock).first().available_quantity == 8 # 10 - 2 = 8
    db.close()
    
    # Segunda entrega DEL MISMO MENSAJE (Redelivered por fallo en red)
    mock_publish.reset_mock()
    main.process_order_created(ch, method, properties, json.dumps(payload))
    
    db2 = TestingSessionLocal()
    # El stock debe SEGUIR SIENDO 8, no 6!
    assert db2.query(Stock).first().available_quantity == 8
    db2.close()
    
    # En la segunda ocasión se confirma ACK pero no se publica doble evento de reserva
    mock_publish.assert_not_called()

@patch("main.publish_stock_response")
def test_process_order_insufficient_stock(mock_publish):
    """
    Verifica que al solicitar más cantidad que el disponible (ej. 15 cuando hay 10),
    el stock no cambia y se responde StockRejected.
    """
    ch = MagicMock()
    method = MagicMock(delivery_tag=3)
    properties = MagicMock()
    
    event_id = str(uuid.uuid4())
    order_id = str(uuid.uuid4())
    payload = {
        "eventId": event_id,
        "orderId": order_id,
        "sku": "LAPTOP-PRO-16",
        "quantity": 50 # Superior al stock de 10
    }
    
    main.process_order_created(ch, method, properties, json.dumps(payload))
    
    db = TestingSessionLocal()
    assert db.query(Stock).first().available_quantity == 10 # Saldo intacto
    db.close()
    
    mock_publish.assert_called_once()
    assert mock_publish.call_args[1]["status"] == "Rejected"
    assert "insuficiente" in mock_publish.call_args[1]["reason"].lower()
