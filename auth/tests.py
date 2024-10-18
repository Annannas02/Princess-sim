import pytest
from flask import json
from auth_service import create_app, db, User

@pytest.fixture
def client():
    app = create_app()
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_register_user(client):
    # Test successful user registration
    response = client.post('/auth/register', json={
        "username": "testuser",
        "password": "password123"
    })
    data = response.get_json()
    
    assert response.status_code == 201
    assert data['msg'] == "User registered successfully"

    # Test duplicate user registration
    response = client.post('/auth/register', json={
        "username": "testuser",
        "password": "password123"
    })
    data = response.get_json()

    assert response.status_code == 409
    assert data['msg'] == "Username already exists"

def test_login_user(client):
    # First, register a user
    client.post('/auth/register', json={
        "username": "testuser",
        "password": "password123"
    })
    
    # Test successful login
    response = client.post('/auth/login', json={
        "username": "testuser",
        "password": "password123"
    })
    data = response.get_json()

    assert response.status_code == 200
    assert "access_token" in data

    # Test login with incorrect password
    response = client.post('/auth/login', json={
        "username": "testuser",
        "password": "wrongpassword"
    })
    data = response.get_json()

    assert response.status_code == 401
    assert data['msg'] == "Invalid credentials"

    # Test login with non-existent user
    response = client.post('/auth/login', json={
        "username": "nonexistentuser",
        "password": "password123"
    })
    data = response.get_json()

    assert response.status_code == 401
    assert data['msg'] == "Invalid credentials"

def test_jwt_protected_endpoint(client):
    # Register and login a user to get an access token
    client.post('/auth/register', json={
        "username": "testuser",
        "password": "password123"
    })
    login_response = client.post('/auth/login', json={
        "username": "testuser",
        "password": "password123"
    })
    access_token = login_response.get_json()["access_token"]

    # Test accessing protected route with valid token
    response = client.get('/auth/user', headers={
        "Authorization": f"Bearer {access_token}"
    })
    data = response.get_json()

    assert response.status_code == 200
    assert data["username"] == "testuser"

    # Test accessing protected route with no token
    response = client.get('/auth/user')
    data = response.get_json()

    assert response.status_code == 401
    assert data['msg'] == "Missing Authorization Header"

    # Test accessing protected route with invalid token
    response = client.get('/auth/user', headers={
        "Authorization": "Bearer invalidtoken"
    })
    data = response.get_json()

    assert response.status_code == 422