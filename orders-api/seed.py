import json
import os
import logging
from sqlalchemy.orm import Session
from models import Stock

logger = logging.getLogger(__name__)

SEED_FILE = os.getenv("SEED_FILE", "/app/seed-data/products.json")

def seed_products(db: Session) -> None:
    """
    Lee el archivo products.json y puebla la tabla 'stock' solo si está vacía.
    Esto permite que el catálogo se administre desde un archivo JSON externo
    en vez de tener INSERTs hardcodeados en SQL.
    """
    existing = db.query(Stock).count()
    if existing > 0:
        logger.info(f"[Seed] La tabla 'stock' ya tiene {existing} productos. Omitiendo seed.")
        return

    if not os.path.exists(SEED_FILE):
        logger.warning(f"[Seed] Archivo {SEED_FILE} no encontrado. No se cargaron productos.")
        return

    try:
        with open(SEED_FILE, "r") as f:
            products = json.load(f)

        for p in products:
            item = Stock(
                sku=p["sku"],
                name=p["name"],
                available_quantity=p["available_quantity"],
                price=p["price"]
            )
            db.merge(item)

        db.commit()
        logger.info(f"[Seed] Se cargaron {len(products)} productos desde {SEED_FILE}")
    except Exception as e:
        db.rollback()
        logger.error(f"[Seed] Error al cargar productos: {e}")
