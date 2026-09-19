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
# NOT: Testler dosya tabanlı SQLite kullanır ve her testten ÖNCE tüm tablolar
# temizlenir (bkz. db_session fixture). Böylece uygulamanın istek handler'ları
# içindeki bağımsız SessionLocal() oturumları da aynı DB'yi görür; dış
# transaction/savepoint sihirine gerek kalmadan çalışır ve veri testler
# arasında taşınmaz.
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"

# Override the database module's settings for testing
import database as db_module
db_module.SQLALCHEMY_DATABASE_URL = TEST_SQLALCHEMY_DATABASE_URL
db_module.engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_module.engine)

# Knowledge seed modülü SessionLocal'i import sırasında tuttuğu için test
# verisinin yanlışlıkla geliştirme sql_app.db'ye yazılmasını engelle.
import knowledge.seed_knowledge as seed_knowledge_module
seed_knowledge_module.SessionLocal = db_module.SessionLocal

# Re-import to get the updated engine and SessionLocal
from database import engine, SessionLocal

# Create the test database tables
Base.metadata.create_all(bind=engine)
# create_all mevcut test_db.db'deki yeni kolonları eklemez; gerçek SQLite
# başlangıcındaki geriye uyumlu şema yükseltmesini test ortamında da çalıştır.
db_module.migrate_schema()


@pytest.fixture(autouse=True)
def _isolated_rate_limits():
    """Her test hız sınırı sayaçlarını sıfırlanmış halde başlatır.

    Rate limit deposu süreç-içi ve anahtar `plan:<feature>:<user_id>`; testler
    aynı kullanıcı (id=1) ile çalıştığından bir testin tükettiği kota sonrakine
    sızıyor ve ilgisiz uçlar 429 dönüyordu. Limitin kendi davranışı
    test_platform_upgrade.test_rate_limit_blocks_after_threshold'da doğrulanır.
    """
    import rate_limit

    rate_limit.reset_memory_store()
    yield
    rate_limit.reset_memory_store()


@pytest.fixture
def db_session():
    """Create a fresh database session for each test.

    Her testten ÖNCE tüm tabloların satırları silinir: önceki testin commit'leri
    bir sonraki teste sızmaz ve testler çalıştırma sırasından bağımsızdır.
    """
    session = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()

    yield session

    session.close()


@pytest.fixture
def client(db_session):
    """Test client; istekler gerçek get_db ile KENDİ taze oturumunu açar.

    NOT: get_db dependency override'ı bilinçli olarak YOKTUR. db_module.get_db'yi
    modül seviyesinde değiştirmek `from database import get_db` ile referansı
    yakalayan modülleri İLK testin oturumuna kilitler ve identity map'ten bayat
    satır okunmasına yol açar (routes_admin'de tespit edildi). Gerçek get_db,
    SessionLocal global'ine dinamik baktığı için test engine'ini (test_db.db)
    zaten kullanır; böylece route oturumları, handler içi SessionLocal()
    kullanımları ve bu fixture'ın oturumu aynı dosya DB'si üzerinden tutarlı
    çalışır. Fixture verisi commit edildiği için istekler her şeyi görür.
    """
    # Import after db_module is patched
    from main import app

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
