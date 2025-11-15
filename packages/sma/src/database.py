"""
Database models and configuration for the SMA.

This module defines the SQLAlchemy models for:
- key_tables: Master keys for HKDF derivation
- registered_devices: Camera registrations with NUC hashes
"""

from typing import List

from sqlalchemy import ARRAY, Column, Integer, LargeBinary, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class KeyTable(Base):
    """
    Master key storage for HKDF key derivation.

    Each row represents one of 2,500 key tables. The master_key is used
    to derive 1,000 encryption keys using HKDF.
    """

    __tablename__ = "key_tables"

    table_id = Column(Integer, primary_key=True, autoincrement=False)
    master_key = Column(LargeBinary(32), nullable=False)  # 256-bit master key

    def __repr__(self) -> str:
        return f"<KeyTable(table_id={self.table_id})>"


class RegisteredDevice(Base):
    """
    Records for provisioned cameras.

    Each device is assigned a unique serial number, has its NUC hash stored,
    and is assigned 3 random key tables for encryption.
    """

    __tablename__ = "registered_devices"

    device_serial = Column(String(255), primary_key=True)
    nuc_hash = Column(LargeBinary(32), nullable=False)  # SHA-256 hash of NUC map
    table_assignments = Column(
        ARRAY(Integer), nullable=False
    )  # List of 3 table IDs (0-2499)
    device_certificate = Column(String, nullable=False)  # PEM-encoded X.509 cert
    device_public_key = Column(String, nullable=False)  # PEM-encoded public key
    device_family = Column(String(50), nullable=False)  # 'Raspberry Pi', 'iOS', etc.

    def __repr__(self) -> str:
        return f"<RegisteredDevice(serial={self.device_serial}, family={self.device_family})>"


# Database session management
engine = None
SessionLocal = None


def init_database(database_url: str) -> None:
    """
    Initialize the database connection.

    Args:
        database_url: PostgreSQL connection string
                     Example: "postgresql://user:pass@localhost/sma"
    """
    global engine, SessionLocal

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Get a database session (dependency for FastAPI).

    Yields:
        Database session

    Example:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
