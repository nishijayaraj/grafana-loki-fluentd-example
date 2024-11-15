from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash 
from random import randint, uniform
import threading
import logging
from sqlalchemy.exc import IntegrityError

# Configure logging
logging.basicConfig(
    filename="./logs/app.log",
    level=logging.INFO,
    format='time="%(asctime)s" logger="%(name)s" level="%(levelname)s" message="%(message)s"'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'plantsarecool1234'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///carnivorous_green_house.db'
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    plants = db.relationship('Plant', backref='owner', lazy=True)

class Plant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    plant_type = db.Column(db.String(50), nullable=False)
    health_data = db.Column(db.String(300), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@app.route('/')
def index():
    error_mode = session.get('error_mode', False)  # Get the current error mode state
    return render_template('index.html', error_mode=error_mode)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error_mode = session.get('error_mode', False)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            logger.info(f'user="{username}" action="create" status="success"')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            logger.error(f'user="{username}" action="signup" status="failed" error="username exists"')
            return render_template('signup.html', error="That username is already taken, please choose another.", error_mode=error_mode), 409
        except Exception as e:
            db.session.rollback()
            logger.exception(f'user="{username}" action="signup" status="error"')
            return render_template('signup.html', error="An unexpected error occurred. Please try again.", error_mode=error_mode), 500
    return render_template('signup.html', error_mode=error_mode)

@app.after_request
def log_response(response):
    logger.info(f'path="{request.path}" method="{request.method}" status="{response.status_code}"')
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_mode = session.get('error_mode', False)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if error_mode and randint(0, 1):
            logger.error(f'user="{username}" action="login" status="error" error="random failure due to error mode"')
            return 'Login Error', 500
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            logger.info(f'user="{username}" action="login" status="success"')
            return redirect(url_for('dashboard'))
        logger.warning(f'user="{username}" action="login" status="failed" error="invalid credentials"')
        return 'Login Failed', 401
    return render_template('login.html', error_mode=error_mode)

@app.after_request
def log_response(response):
    logger.info(f'path="{request.path}" method="{request.method}" status="{response.status_code}"')
    return response

@app.route('/logout')
def logout():
    error_mode = session.get('error_mode', False)
    username = session.get('username', 'unknown')
    if error_mode and randint(0, 1):
        logger.error(f'user="{username}" action="logout" status="error" error="Failed to loggout."')
        return "Logout Error", 500
    session.pop('user_id', None)
    logger.info(f'user="{username}" action="logout" status="success"')
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET'])
def dashboard():
    error_mode = session.get('error_mode', False)
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    plants = Plant.query.filter_by(user_id=user_id).all()
    return render_template('dashboard.html', user=user, plants=plants, error_mode=error_mode)

@app.route('/toggle_error_mode', methods=['POST'])
def toggle_error_mode():
    current_mode = session.get('error_mode', False)
    session['error_mode'] = not current_mode
    session.modified = True
    logger.info(f"Error mode toggled to {'on' if session['error_mode'] else 'off'}.")
    return redirect(request.referrer or url_for('index'))

@app.after_request
def log_response(response):
    logger.info(f'path="{request.path}" method="{request.method}" status="{response.status_code}"')
    return response

@socketio.on('add_plant')
def handle_add_plant(json):
    user_id = session.get('user_id')
    if not user_id or (session.get('error_mode', False) and randint(0, 1)):
        logger.error("Unauthorized or failed attempt to add plant.")
        emit('error', {'error': 'Failed to add plant due to server error'}, room=request.sid)
        return
    plant_name = json.get('plant_name')
    plant_type = json.get('plant_type')
    new_plant = Plant(name=plant_name, plant_type=plant_type, health_data="Healthy", user_id=user_id)
    db.session.add(new_plant)
    db.session.commit()
    emit('new_plant', {'plant_id': new_plant.id, 'plant_name': new_plant.name, 'plant_type': new_plant.plant_type}, room=str(user_id))
    logger.info(f"New plant {plant_name} added successfully.")


active_users = {}

@socketio.on('connect')
def handle_connect():
    user_id = session.get('user_id')
    if user_id:
        active_users[user_id] = {'error_mode': session.get('error_mode', False)}
        join_room(str(user_id))
        logger.info(f"User {user_id} connected and joined their room with error mode {active_users[user_id]['error_mode']}.")

@socketio.on('disconnect')
def on_disconnect():
    user_id = session.get('user_id')
    if user_id in active_users:
        del active_users[user_id]
        logger.info(f"User {user_id} disconnected and was removed from active list.")

def simulate_plant_data():
    while True:
        with app.app_context():
            socketio.sleep(2)  # Sleep for 10 seconds
            for user_id, user_info in list(active_users.items()):
                try:
                    if user_info['error_mode'] and randint(0, 1):
                        logger.error(f"Failed to send data to: {user_id}: Will retry later")
                        continue
                    plants = Plant.query.filter_by(user_id=user_id).all()
                    for plant in plants:
                        fake_data = {
                            'temperature': round(uniform(20.0, 30.0), 2),
                            'humidity': round(uniform(40.0, 60.0), 2),
                            'water_level': randint(1, 10),
                            'number_of_insects': randint(0, 10)
                        }
                        socketio.emit('update_plant', {'plant_id': plant.id, 'data': fake_data}, room=str(user_id))
                        logger.debug(f"Simulated data for plant {plant.id} sent to user {user_id}")
                except Exception as e:
                    logger.error(f"Error in simulation thread for user {user_id}: {str(e)}")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.start_background_task(simulate_plant_data)
    socketio.run(app=app, host="0.0.0.0", port=5005, allow_unsafe_werkzeug=True)
