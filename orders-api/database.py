import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Obtener URL de DB desde variables de entorno con fallback para desarrollo local
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://q10_admin:secure_password_q10@localhost:5432/q10_orderflow_db")

# Si estamos corriendo en modo test (ej. SQLite o DB paralela) se puede ajustar aquí
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency para inyectar la sesión de la base de datos en los endpoints de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
