from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import bcrypt
import time
import requests

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost:8900/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'  # Change this for production
db = SQLAlchemy(app)
jwt = JWTManager(app)

# User Model
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # This will store the hashed password
    created_at = db.Column(db.DateTime, default=db.func.now())

    
with app.app_context():
    db.create_all()

def register_with_consul(service_name, service_id, service_port):
    url = "http://localhost:8500/v1/agent/auth/register"
    data = {
        "Name": service_name,
        "ID": service_id,
        "Address": "localhost",
        "Port": service_port,
        "Tags": ["flask", service_name]
    }
    requests.put(url, json=data)

@app.route('/auth/status', methods=['GET'])
def status():
    return jsonify({"status": "Auth service is up and running!"}), 200

# Registration endpoint with password hashing
@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 409
    
    # Hash the password using bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Create new user with hashed password
    new_user = User(username=username, password=hashed_password.decode('utf-8'))
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"msg": "User registered successfully"}), 201

# Login endpoint with password hashing verification
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # Find user
    user = User.query.filter_by(username=username).first()
    
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({"msg": "Invalid credentials"}), 401
    
    # Create access token
    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token)

# Protected route to get user details
@app.route('/auth/user', methods=['GET'])
@jwt_required()
def get_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"msg": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "created_at": user.created_at
    })

@app.route('/auth/users', methods=['GET'])
def get_users():
    users = User.query.all()
    
    # Create a list of dictionaries for each user
    users_list = []
    for user in users:
        users_list.append({
            "id": user.id,
            "username": user.username,
            "created_at": user.created_at
        })
    
    return jsonify(users=users_list), 200

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True, port=5050)
    register_with_consul("auth-service", "auth-service-id", 5050)  # For auth_service
