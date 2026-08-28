"""Test authentication functionality."""
import pytest
from sqlalchemy.orm import Session
from fastapi import status
from main import app
import auth, models, schemas
from database import Base, engine, SessionLocal


def test_create_access_token():
    """Test JWT token creation."""
    data = {"sub": "123"}
    token = auth.create_access_token(data)
    assert isinstance(token, str)
    assert len(token) > 0


def test_authenticate_user(db_session: Session):
    """Test user authentication."""
    # Create a test user
    user = models.User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=auth.hash_password("securepassword123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Authenticate with correct credentials
    authenticated = auth.authenticate_user(db_session, "test@example.com", "securepassword123")
    assert authenticated is not None
    assert authenticated.id == user.id
    assert authenticated.email == "test@example.com"

    # Authenticate with incorrect password
    authenticated = auth.authenticate_user(db_session, "test@example.com", "wrongpassword")
    assert authenticated is None

    # Authenticate with non-existent email
    authenticated = auth.authenticate_user(db_session, "nonexistent@example.com", "securepassword123")
    assert authenticated is None


def test_get_user_by_email(db_session: Session):
    """Test getting user by email."""
    # Create a test user
    user = models.User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=auth.hash_password("securepassword123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Get existing user
    found_user = auth.get_user_by_email(db_session, "test@example.com")
    assert found_user is not None
    assert found_user.id == user.id

    # Get non-existent user
    found_user = auth.get_user_by_email(db_session, "nonexistent@example.com")
    assert found_user is None


def test_hash_password():
    """Test password hashing."""
    password = "securepassword123"
    hashed = auth.hash_password(password)
    assert hashed != password
    assert len(hashed) > 0
    # Verify the hash
    assert auth.verify_password(password, hashed)
    assert not auth.verify_password("wrongpassword", hashed)


def test_register_endpoint(client):
    """Test user registration endpoint."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "New User"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["full_name"] == "New User"
    assert data["user"]["id"] is not None


def test_register_duplicate_email(client):
    """Test registration with duplicate email."""
    # First registration
    client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "securepassword123",
            "full_name": "First User"
        }
    )

    # Second registration with same email
    response = client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "differentpassword456",
            "full_name": "Second User"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "zaten kullanımda" in response.json()["detail"]


def test_login_endpoint(client):
    """Test login endpoint."""
    # Create a user first
    client.post(
        "/api/auth/register",
        json={
            "email": "loginuser@example.com",
            "password": "securepassword123",
            "full_name": "Login User"
        }
    )

    # Test login
    response = client.post(
        "/api/auth/login",
        json={
            "email": "loginuser@example.com",
            "password": "securepassword123"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "loginuser@example.com"


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    # Create a user first
    client.post(
        "/api/auth/register",
        json={
            "email": "baddata@example.com",
            "password": "securepassword123",
            "full_name": "Bad Data User"
        }
    )

    # Test with wrong password
    response = client.post(
        "/api/auth/login",
        json={
            "email": "baddata@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Test with non-existent email
    response = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "securepassword123"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user(client):
    """Test getting current user info."""
    # Register and login
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "currentuser@example.com",
            "password": "securepassword123",
            "full_name": "Current User"
        }
    )
    token = register_response.json()["access_token"]

    # Get current user
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "currentuser@example.com"
    assert data["full_name"] == "Current User"


def test_get_current_user_unauthorized(client):
    """Test getting current user without token."""
    response = client.get("/api/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_invalid_token(client):
    """Test getting current user with invalid token."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED