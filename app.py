from flask import render_template, redirect, url_for, request, flash, Flask
from flask_login import login_user, login_required, logout_user, current_user, LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta
import atexit


app = Flask(__name__)
app.config['SECRET_KEY'] = 'MY_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'  # Database file will be created in the project folder
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
class Task(db.Model):
    """class define every parameter that we need to use for defining Task"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    alert_hours = db.Column(db.Time, nullable=False)
    completed = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('tasks', lazy=True))

class User(UserMixin, db.Model):
    """Class define every parameter we need to use for defininnig the user"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
@login_manager.user_loader
def load_user(user_id):
    """Loading id of the user"""
    return User.query.get(int(user_id))
@app.route("/")
def index():
    """Welcomming route"""
    return render_template('index.html')
@login_manager.unauthorized_handler
def unauthorized():
    """Login manager"""
    flash('You must be logged in to access that page.', 'danger')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register page that make user register and save the information"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different username.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page that make user login to the dashboard page """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page that show the user all to do tasks"""
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    current_time = datetime.now()
    return render_template('dashboard.html', tasks=tasks, current_time=current_time)

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    """Add_task page make user adding new task"""
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date_str = request.form['due_date']
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        alert_hours_str = request.form['alert_hours']
        alert_hours = datetime.strptime(alert_hours_str, '%H:%M').time()

        new_task = Task(title=title, description=description, due_date=due_date, user_id=current_user.id, alert_hours=alert_hours)
        db.session.add(new_task)
        db.session.commit()

        flash('Task added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_task.html')
def check_task_deadline():
    """Check upcoming tasks deadline"""
    now = datetime.now()
    tasks = Task.query.filter_by(completed=False).all()

    for task in tasks:
        alert_time = datetime.combine(task.due_date, task.alert_hours)
        if now >= alert_time - timedelta(hours=1):
            print(f"alert: Task '{Task.title}' is approaching its deadline at {alert_time}.")
    scheduler = BackgroundScheduler
    scheduler.add_job(func=check_task_deadline, trigger="interval", minutes=1)
    scheduler.start()

    atexit.register(lambda:scheduler.shutdown())

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    """Make user edit for exisiting tasks"""
    task = Task.query.get_or_404(task_id)

    if task.user_id != current_user.id:
        flash('You are not authorized to edit this task.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        if request.form['due_date']:
            task.due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d')
        else:
            flash('Due date is required!', 'warning')
        alert_hours_str = request.form['alert_hours']
        task.alert_hours = datetime.strptime(alert_hours_str, '%H:%M').time()
        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_task.html', task=task)


@app.route('/delete_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def delete_task(task_id):
    """Make user delete task if itis done"""
    task = Task.query.get_or_404(task_id)

    if task.user_id != current_user.id:
        flash('You are not authorized to delete this task.', 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(task)
    db.session.commit()

    flash('Task deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    """Make user logout from the task session"""
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
