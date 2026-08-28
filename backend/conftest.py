"""Pytest fixtures and configuration for backend tests."""
import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import models
from database import Base
import auth
import crud
import schemas

# Use a separate database file for tests
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"

# Override the database module's settings for testing
import database as db_module
db_module.SQLALCHEMY_DATABASE_URL = TEST_SQLALCHEMY_DATABASE_URL
db_module.engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_module.engine)

# Re-import to get the updated engine and SessionLocal
from database import engine, SessionLocal, get_db

# Create the test database tables
Base.metadata.create_all(bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    # Override get_db dependency.
    # NOT: Oturumu burada KAPATMIYORUZ - bu jeneratör FastAPI tarafından HER istekte
    # çağrılır; bir testte birden fazla client.post/get çağrısı yapıldığında (örn.
    # register + refresh akışı) session ilk istekten sonra kapanıp ikinci istekte
    # "This Session/Connection is closed" hatası verirdi. Gerçek kapatma işlemi bu
    # fixture'ın sonundaki `session.close()` satırında yapılıyor.
    def override_get_db():
        yield session

    db_module.get_db = override_get_db

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Create a test client with the overridden database."""
    # Import after db_module is patched
    from main import app

    # Override the get_db dependency
    app.dependency_overrides[get_db] = lambda: (yield db_session)

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_user(db_session):
    """Create a test user and return credentials."""
    user = models.User(
        email="testuser@test.com",
        full_name="Test User",
        hashed_password=auth.hash_password("testpassword123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_profile(db_session, test_user):
    """Create a test profile for the test user."""
    profile = crud.get_or_create_profile(db_session, test_user.id)
    profile.onboarding_completed = True
    profile.daily_calorie_target = 2200
    profile.daily_protein_target = 140
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def auth_token(test_user):
    """Generate a valid JWT token for the test user."""
    return auth.create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def auth_headers(auth_token):
    """Return authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}