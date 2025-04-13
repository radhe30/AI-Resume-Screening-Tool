import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email
import fitz  # PyMuPDF
import torch
from transformers import DistilBertTokenizer, DistilBertModel
from sklearn.metrics.pairwise import cosine_similarity

# Initialize Flask app, Bcrypt, SQLAlchemy, and LoginManager
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this to a random secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Path to SQLite database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_description = db.Column(db.String(255), nullable=False)
    resume_name = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<Resume {self.resume_name}, Score {self.score}>"

# Initialize the database
with app.app_context():
    db.create_all()

# Define the login form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

# Routes for user authentication
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))  # Redirect to dashboard if already logged in
    
    form = RegistrationForm()  # Create the registration form

    if form.validate_on_submit():  # Check if form is submitted and valid
        email = form.email.data
        password = form.password.data
        
        # Check if email already exists in the database
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('login'))
        
        # Hash the password using bcrypt
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Create a new User instance and save it to the database
        new_user = User(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Your account has been created!', 'success')
        
        # Log the user in immediately after registration
        login_user(new_user)
        
        return redirect(url_for('dashboard'))  # Redirect to dashboard after successful registration
    
    return render_template('register.html', title='Register', form=form)  # Render the registration form template


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))  # Redirect to dashboard if user is logged in
    
    form = LoginForm()  # Initialize your LoginForm
    
    if form.validate_on_submit():  # Check if form is submitted and validated
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()  # Fetch user by email
        
        if user and check_password_hash(user.password, password):  # Check if user exists and passwords match
            login_user(user)  # Log the user in
            flash('You have been logged in!', 'success')  # Success message
            return redirect(url_for('dashboard'))  # Redirect to dashboard
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')  # Failure message
    
    return render_template('login.html', title='Login', form=form)  # Always return the login template


@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Route for home page (index)
#@app.route('/')
#def index():
 #   return render_template('index.html')
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))
# Handle resume upload and screening
@app.route('/upload', methods=['POST'])
@login_required
def upload_files():
    if 'job_description' not in request.files or 'resumes' not in request.files:
        return "Missing files", 400

    job_description = request.files['job_description']
    resumes = request.files.getlist('resumes')

    # Save job description
    job_desc_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(job_description.filename))
    job_description.save(job_desc_path)

    # Save resumes
    resume_paths = []
    for resume in resumes:
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(resume.filename))
        resume.save(resume_path)
        resume_paths.append(resume_path)

    # Match resumes
    ranked_resumes = match_resumes(job_desc_path, resume_paths)

    # Save ranking results to the database
    for resume_path, score in ranked_resumes:
        resume_name = resume_path.split('/')[-1]
        new_resume = Resume(job_description=job_desc_path, resume_name=resume_name, score=score)
        db.session.add(new_resume)

    db.session.commit()

    return render_template('result.html', rankings=ranked_resumes)

# Function to extract text from PDFs
def extract_text_from_pdf(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()
    return text

# Load DistilBERT model and tokenizer
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
model = DistilBertModel.from_pretrained('distilbert-base-uncased')

def get_text_embedding(text):
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings

def match_resumes(job_desc_path, resume_paths):
    job_text = extract_text_from_pdf(job_desc_path)
    resumes_text = [extract_text_from_pdf(resume) for resume in resume_paths]

    job_embedding = get_text_embedding(job_text)
    resume_embeddings = [get_text_embedding(resume) for resume in resumes_text]

    similarities = []
    for resume_embedding in resume_embeddings:
        similarity = cosine_similarity(job_embedding.numpy(), resume_embedding.numpy())
        similarities.append(similarity[0][0])

    ranked_resumes = sorted(zip(resume_paths, similarities), key=lambda x: x[1], reverse=True)
    return ranked_resumes

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
