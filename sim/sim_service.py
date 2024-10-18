from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_socketio import SocketIO, send, join_room, leave_room, disconnect
import redis
import requests
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Initialize SocketIO

redis_client = redis.StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=0)

# Configuration for the simulation service's database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'postgresql://test_user:test_password@db:5432/test_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'  # Use the same secret key as the Authentication Service
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Princess Details Model
class PrincessDetails(db.Model):
    __tablename__ = 'princess_details'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    mood_level = db.Column(db.Integer, default=0, nullable=False)

# Servant Details Model
class ServantDetails(db.Model):
    __tablename__ = 'servant_details'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    skill_level = db.Column(db.Integer, default=0, nullable=False)

# Tasks Model
class Tasks(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)

# Session Model
class Session(db.Model):
    __tablename__ = 'sessions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    start_timestamp = db.Column(db.DateTime, default=db.func.now())
    end_timestamp = db.Column(db.DateTime)
    
    princess_id = db.Column(db.Integer, db.ForeignKey('princess_details.id'), nullable=False)
    servant_id = db.Column(db.Integer, db.ForeignKey('servant_details.id'), nullable=False)

    host_port = db.Column(db.Integer)


# Request Model
class Request(db.Model):
    __tablename__ = 'requests'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    timestamp = db.Column(db.DateTime, default=db.func.now())
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    
    success = db.Column(db.Boolean, nullable=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    princess_id = db.Column(db.Integer, db.ForeignKey('princess_details.id'),nullable=False)
    servant_id = db.Column(db.Integer, db.ForeignKey('servant_details.id'),nullable=False) 


# Session Log Model
class SessionLog(db.Model):
    __tablename__ = 'session_log'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)


with app.app_context():
    db.drop_all()
    db.create_all()

import jwt as PyJWT

def process_jwt(token):
    try:
        decoded_payload = PyJWT.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=["HS256"])
        return decoded_payload.get("sub")

    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# Handling a user joining a room
@socketio.on('join_room')
def handle_join(data):

    # Get room
    room_id = request.args.get('room_id')
    if not room_id:
        send('ERROR: room_id was not provided!')
        disconnect()
        return
    
    # Check room
    session = Session.query.filter_by(id=room_id).first()
    if not session or session.host_port != int(os.getenv('PORT')):
        send(f'{session.host_port}')
        disconnect()
        return
    
    # Check user
    token = request.headers.get('Authorization')
    user_id = process_jwt(token.split(' ')[1])
    char_details = None
    char_details = ServantDetails.query.filter_by(user_id=user_id).first()
    if not char_details:
        char_details = PrincessDetails.query.filter_by(user_id=user_id).first()
    if not char_details:
        send(f'{user_id}, {session.princess_id}, {session.servant_id}')
        disconnect()
        return
    
    # Get role
    role = None
    try:
        mood_level = char_details.mood_level
        role = "Princess"
    except AttributeError:
        role = "Servant"
    
    join_room(room_id)
    send(f'{role} has connected.', room=room_id, broadcast=True)


# Handling messages sent to a room
@socketio.on('send_message')
def handle_message(data):

    # Get room
    room_id = request.args.get('room_id')
    if not room_id:
        send('ERROR: room_id was not provided!')
        disconnect()
        return
    
    # Check room
    session = Session.query.filter_by(id=room_id).first()
    if not session or session.host_port != int(os.getenv('PORT')):
        send('ERROR: This is an unauthorized access attempt! (1)')
        disconnect()
        return
    
    # Check user
    token = request.headers.get('Authorization')
    user_id = process_jwt(token.split(' ')[1])
    char_details = None
    char_details = ServantDetails.query.filter_by(user_id=user_id).first()
    if not char_details:
        char_details = PrincessDetails.query.filter_by(user_id=user_id).first()
    if not char_details:
        send(f'{user_id}, {session.princess_id}, {session.servant_id}')
        disconnect()
        return
    
    # Get role
    role = None
    try:
        mood_level = char_details.mood_level
        role = "Princess"
    except AttributeError:
        role = "Servant"

    message = data['message']
    
    send(f'{role}: {message}', room=room_id, broadcast=True)


# Handling a user leaving a room
@socketio.on('leave_room')
def handle_disconnect(data):

   # Get room
    room_id = request.args.get('room_id')
    if not room_id:
        send('ERROR: room_id was not provided!')
        disconnect()
        return
    
    # Check room
    session = Session.query.filter_by(id=room_id).first()
    if not session or session.host_port != int(os.getenv('PORT')):
        send('ERROR: This is an unauthorized access attempt! (1)')
        disconnect()
        return
    
    # Check user
    token = request.headers.get('Authorization')
    user_id = process_jwt(token.split(' ')[1])
    char_details = None
    char_details = ServantDetails.query.filter_by(user_id=user_id).first()
    if not char_details:
        char_details = PrincessDetails.query.filter_by(user_id=user_id).first()
    if not char_details:
        send(f'{user_id}, {session.princess_id}, {session.servant_id}')
        disconnect()
        return
    
    # Get role
    role = None
    try:
        mood_level = char_details.mood_level
        role = "Princess"
    except AttributeError:
        role = "Servant"

    leave_room(room_id)
    
    send(f'{role} has disconnected.', room=room_id, broadcast=True)

    disconnect()

def register_with_consul(service_name, service_id, service_port):
    url = "http://localhost:8500/v1/agent/sim/register"
    data = {
        "Name": service_name,
        "ID": service_id,
        "Address": "localhost",
        "Port": service_port,
        "Tags": ["flask", service_name]
    }
    requests.put(url, json=data)

@app.route('/simulation/status', methods=['GET'])
def status():
    return jsonify({"status": "Simulation service is up and running!"}), 200

@app.route('/simulation/add_user', methods=['POST'])
@jwt_required()
def add_user():
    user_id = get_jwt_identity()  # Get the current user ID from the JWT
    data = request.get_json()

    # Boolean flag to determine whether to add as princess or servant
    is_princess = data.get('is_princess')

    if is_princess is None:
        return jsonify({"msg": "Missing 'is_princess' field in request data"}), 400

    if is_princess:
        # Check if the user already exists as a princess
        if PrincessDetails.query.filter_by(user_id=user_id).first():
            return jsonify({"msg": "User is already a princess"}), 400
        
        # Create a new princess character
        new_princess = PrincessDetails(user_id=user_id, mood_level=50)
        db.session.add(new_princess)
        db.session.commit()

        return jsonify({"msg": "Princess created successfully", "princess_id": new_princess.id}), 201
    else:
        # Check if the user already exists as a servant
        if ServantDetails.query.filter_by(user_id=user_id).first():
            return jsonify({"msg": "User is already a servant"}), 400
        
        # Create a new servant character
        new_servant = ServantDetails(user_id=user_id, skill_level=1)
        db.session.add(new_servant)
        db.session.commit()

        return jsonify({"msg": "Servant created successfully", "servant_id": new_servant.id}), 201


@app.route('/simulation/princess/details', methods=['GET'])
@jwt_required()
def get_princess_details():
    user_id = get_jwt_identity()
    princess = PrincessDetails.query.filter_by(user_id=user_id).first()
    
    if not princess:
        return jsonify({"msg": "Princess details not found"}), 404
    
    return jsonify({
        "id": princess.id,
        "user_id": princess.user_id,
        "mood_level": princess.mood_level,
    })

@app.route('/simulation/servant/details', methods=['GET'])
@jwt_required()
def get_servant_details():
    user_id = get_jwt_identity()
    servant = ServantDetails.query.filter_by(user_id=user_id).first()
    
    if not servant:
        return jsonify({"msg": "Servant details not found"}), 404
    
    return jsonify({
        "id": servant.id,
        "user_id": servant.user_id,
        "skill_level": servant.skill_level,
    })

@app.route('/simulation/request/task', methods=['POST'])
@jwt_required()
def request_task():
    user_id = get_jwt_identity()
    data = request.get_json()

    task_id = data.get('task_id')
    session_id = data.get('session_id')  # Assume we get a valid session_id from the client
    princess = PrincessDetails.query.filter_by(user_id=user_id).first()
    # Validate the task
    task = Tasks.query.filter_by(id=task_id).first()
    if not task:
        return jsonify({"msg": "Invalid task ID"}), 400

    # Validate the session
    session = Session.query.filter_by(id=session_id, end_timestamp=None).first()
    if not session:
        return jsonify({"msg": "Invalid session or session not found"}), 404
    servant = ServantDetails.query.filter_by(user_id=session.servant_id).first()

    # Create a new request
    new_request = Request(
        task_id=task_id,
        princess_id=princess.id,  # Assuming user_id matches princess_details_id
        servant_id=servant.id,
        session_id=session_id,
        timestamp=db.func.now() 
    )
    db.session.add(new_request)
    db.session.commit()

    # Create a log entry in SessionLog for the new request
    new_log = SessionLog(
        session_id=session.id,
        request_id=new_request.id
    )
    db.session.add(new_log)
    db.session.commit()

    return jsonify({"msg": "Task request created and logged", "request_id": new_request.id, "log_id": new_log.id}), 201


@app.route('/simulation/session/start', methods=['POST'])
@jwt_required()
def start_session():
    user_id = get_jwt_identity()
    data = request.get_json()

    servant_id = data.get('servant_id')

    princess = PrincessDetails.query.filter_by(user_id=user_id).first()
    
    if not princess:
        return jsonify({"msg": "Princess details not found"}), 404
    
    # Start a new session
    new_session = Session(
        princess_id=princess.id,
        servant_id=servant_id,
        start_timestamp=db.func.now(),
        host_port = int(os.getenv('PORT'))
    )
    db.session.add(new_session)
    db.session.commit()

    session_key = f"session:{new_session.id}"
    session_data = {
        "princess_mood": princess.mood_level,
        "servant_skill": 1  # Assuming initial skill level
    }

    return jsonify({"msg": "Session started", "session_id": new_session.id, "host_port": new_session.host_port}), 201


@app.route('/simulation/session/servants-current', methods=['GET'])
@jwt_required()
def get_current_session():
    user_id = get_jwt_identity()  # Get the current user ID from the JWT

    # Fetch the servant's details
    servant = ServantDetails.query.filter_by(user_id=user_id).first()
    
    if not servant:
        return jsonify({"msg": "Servant details not found"}), 404

    # Find the active session for the servant (where end_timestamp is None)
    session = Session.query.filter_by(servant_id=servant.id, end_timestamp=None).first()

    if not session:
        return jsonify({"msg": "No active session found for the servant"}), 404

    # Return the session details as in /simulation/session/start
    return jsonify({
        "msg": "Current session found",
        "session_id": session.id,
        "host_port": session.host_port
    }), 200


@app.route('/simulation/session/end', methods=['POST'])
@jwt_required()
def end_session():
    data = request.get_json()

    session_id = data.get('session_id')
    session = Session.query.filter_by(id=session_id).first()

    if not session:
        return jsonify({"msg": "Session not found or already completed"}), 404

    # End the session
    session.end_timestamp = db.func.now()
    db.session.commit()

    return jsonify({"msg": "Session ended"}), 200


@app.route('/simulation/session/logs', methods=['GET'])
def get_session_logs():
    data = request.get_json()
    session_id = data.get('session_id')
    
    session_logs = SessionLog.query.filter_by(session_id=session_id).all()
    
    if not session_logs:
        return jsonify({"msg": "No logs found for this session"}), 404
    
    logs = []
    for log in session_logs:
        logs.append({
            "log_id": log.id,
            "session_id": log.session_id,
            "request_id": log.request_id
        })
    
    return jsonify({"logs": logs}), 200

@app.route('/simulation/request/complete', methods=['POST'])
@jwt_required()
def complete_request():
    user_id = get_jwt_identity()
    data = request.get_json()

    request_id = data.get('request_id')
    
    # Fetch the request to be completed
    task_request = Request.query.filter_by(id=request_id).first()

    if not task_request:
        return jsonify({"msg": "Request not found or unauthorized"}), 404

    # Mark the request as completed
    task_request.success = True
    db.session.commit()

    return jsonify({"msg": "Request completed", "request_id": task_request.id}), 200

# Run the Flask p
if __name__ == '__main__':
    socketio.run(app, debug=True, port=os.getenv('PORT'), host='0.0.0.0')
    register_with_consul("simulation-service", "simulation-service-id", os.getenv('PORT'))  # For sim_service

