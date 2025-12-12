"""Main FastAPI application for Birthmark Blockchain Node."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.shared.config import settings
from src.shared.crypto.signatures import ValidatorKeys
from src.aggregator.api import submissions, modifications
from src.node.api import verification, status
from src.node.api import blockchain

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.

    Handles startup and shutdown tasks.
    """
    logger.info(f"Starting Birthmark Blockchain Node: {settings.node_id}")
    logger.info(f"Consensus mode: {settings.consensus_mode}")

    # Load or generate validator keys
    validator_keys = load_or_generate_keys()
    logger.info(f"Loaded validator keys: {validator_keys.validator_id}")

    yield  # Application is running

    # Shutdown
    logger.info("Shutting down Birthmark Blockchain Node")


def load_or_generate_keys() -> ValidatorKeys:
    """Load validator keys from file or generate new ones."""
    key_path = Path(settings.validator_key_path)

    if key_path.exists():
        logger.info(f"Loading validator keys from {key_path}")
        return ValidatorKeys.load_from_file(key_path)
    else:
        logger.warning(f"No keys found at {key_path}, generating new keys")
        keys = ValidatorKeys.generate()
        keys.save_to_file(key_path)
        logger.info(f"Saved new validator keys to {key_path}")
        return keys


# Create FastAPI application
app = FastAPI(
    title="Birthmark Blockchain Node",
    description="Merged aggregator and blockchain validator for Birthmark Standard",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(submissions.router)  # Camera submission API
app.include_router(modifications.router)  # Modification tracking (Phase 3)
app.include_router(verification.router)  # Public verification API
app.include_router(status.router)  # Health and status
app.include_router(blockchain.router)  # Phase 1 blockchain node


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "service": "Birthmark Blockchain Node",
        "node_id": settings.node_id,
        "version": "0.1.0",
        "consensus_mode": settings.consensus_mode,
    }


def main():
    """Main entry point."""
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=1,  # Must be 1 for background tasks
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
