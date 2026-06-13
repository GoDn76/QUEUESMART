import asyncio
import logging
from sqlalchemy.future import select
from app.db.session import engine, Base, async_session_maker
from app.models.models import Organization, Counter, ServiceType
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Initialize database tables and create mock data for development."""
    logger.info("Initializing database tables...")
    
    max_retries = 10
    retry_delay = 2  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                # Import models so SQLAlchemy registers them
                from app.models import models
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized successfully.")
            break
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Database connection failed after {max_retries} attempts.")
                raise e
            logger.warning(
                f"Database connection attempt {attempt}/{max_retries} failed: {e}. "
                f"Retrying in {retry_delay}s..."
            )
            await asyncio.sleep(retry_delay)

    # Insert initial mock data for demo if database is empty
    async with async_session_maker() as session:
        # Check if an organization already exists
        result = await session.execute(select(Organization).limit(1))
        existing_org = result.scalars().first()

        if not existing_org:
            logger.info("Creating mock organization, counters, and service types...")
            try:
                # Create Mock Org
                mock_org = Organization(
                    name="City Hospital",
                    email="admin@cityhospital.com",
                    hashed_password=get_password_hash("admin123")
                )
                session.add(mock_org)
                await session.flush()  # Populate mock_org.id

                # Create Service Types
                emergency_service = ServiceType(
                    organization_id=mock_org.id,
                    name="Emergency Consultation",
                    estimated_duration_minutes=10,
                    priority_weight=100
                )
                general_service = ServiceType(
                    organization_id=mock_org.id,
                    name="General OPD",
                    estimated_duration_minutes=20,
                    priority_weight=50
                )
                billing_service = ServiceType(
                    organization_id=mock_org.id,
                    name="Billing & Discharge",
                    estimated_duration_minutes=15,
                    priority_weight=10
                )
                session.add_all([emergency_service, general_service, billing_service])

                # Create Counters
                billing_counter = Counter(
                    organization_id=mock_org.id,
                    name="Billing Counter 1",
                    queue_type="FIFO",
                    qr_slug="hospital-billing",
                    active=True
                )
                opd_counter = Counter(
                    organization_id=mock_org.id,
                    name="OPD Counter A",
                    queue_type="HYBRID",
                    qr_slug="opd-counter-a",
                    active=True
                )
                session.add_all([billing_counter, opd_counter])

                await session.commit()
                logger.info("Mock database contents seeded successfully.")
            except Exception as e:
                await session.rollback()
                logger.error(f"Error seeding mock database contents: {e}")
        else:
            logger.info("Database already contains records, skipping seeding.")
