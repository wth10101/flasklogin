import sqlite3
from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import bcrypt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key' # for teaching, should not be stored here

login_manager = LoginManager(app)  # creates an object that hndles the flask login features
login_manager.login_view = 'login' # giving us access to the login manager decorator

# --- Database Helper ---
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

# Create table and a dummy user at startup
def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, 
                 username TEXT UNIQUE, 
                 password TEXT,
                 level INTEGER)''')
    
    # Create a default user if they don't exist
    hashed_pw = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt())
    try:
        conn.execute('INSERT INTO users (username, password,level) VALUES (?, ?, ?)', ('admin', hashed_pw,0))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # User already exists
    conn.close()

# --- User Class for Flask-Login ---
class User(UserMixin):
    def __init__(self, id, username,level):
        self.id = id
        self.username = username
        self.level = level

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], level = user_data['level'])
    return None

# --- Routes ---
@app.route('/login', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user_row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user_row and bcrypt.checkpw(password.encode('utf-8'), user_row['password'], ):
            user_obj = User(id=user_row['id'], username=user_row['username'], level=user_row['level'])
            login_user(user_obj)                  # will log the user in on the login manger
            if current_user.level == 0:
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('quiz')) # current_user accesible in template
        
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    user_data = conn.execute('SELECT username, level FROM users').fetchall()
    print(user_data)
    conn.close()
    return render_template('dashboard.html', users=user_data)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 1. Hash the password before storing it
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # 2. Insert into the database
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password, level) VALUES (?, ?, ?)', 
                         (username, hashed_pw, 1)) # default new user to level 1
            conn.commit()
            conn.close()
            # Redirect to login so they can sign in with their new account
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return "Username already exists. Please choose another."

    return render_template('register.html')

@app.route('/quiz')
@login_required
def quiz():
    return render_template('quiz.html')

@app.route('/levelup')
@login_required
def levelup():
    current_user.level += 1
    conn = get_db_connection()
    conn.execute("UPDATE users SET level = ? WHERE id = ?", (current_user.level, current_user.id))
    conn.commit()
    conn.close()
    return render_template('quiz.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)