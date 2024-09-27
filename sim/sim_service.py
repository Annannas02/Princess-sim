from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

app = Flask(__name__)

# Configuration for the simulation service's database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost:8950/postgres'
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
    princess_id = db.Column(db.Integer, db.ForeignKey('princess_details.id'),nullable=False)
    servant_id = db.Column(db.Integer, db.ForeignKey('servant_details.id'),nullable=False) 


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
    db.create_all()

@app.route('/add_user', methods=['POST'])
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



@app.route('/princess/details', methods=['GET'])
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

@app.route('/servant/details', methods=['GET'])
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

@app.route('/request/task', methods=['POST'])
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


@app.route('/session/start', methods=['POST'])
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
        start_timestamp=db.func.now() 
    )
    db.session.add(new_session)
    db.session.commit()

    return jsonify({"msg": "Session started", "session_id": new_session.id}), 201

@app.route('/session/end', methods=['POST'])
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


@app.route('/session/logs', methods=['GET'])
@jwt_required()
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

@app.route('/request/complete', methods=['POST'])
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

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
