import os
import csv
from flask import Flask, request, redirect, url_for, render_template, flash, Response
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pandas as pd
from apyori import apriori


app = Flask(__name__)

app.config['UPLOAD_FOLDER'] ='uploads'

app.config['PERMANENT_SESSION_LIFETIME'] = 1800

app.secret_key = 'your_secret_key_here'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id_, email, password):
        self.id = id_
        self.email = email
        self.password = password

    @staticmethod
    def get(user_id):
        # Load users from CSV file
        with open('users.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if int(row['id']) == user_id:
                    return User(user_id, row['email'], row['password'])

    @staticmethod
    def find(email):
        # Find user by email in CSV file
        with open('users.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['email'] == email:
                    return User(int(row['id']), row['email'], row['password'])

@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/products')
def products():
    return render_template('products.html')

@app.route('/learnmore')
def learn_more():
    return render_template('learn-more.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's name from session or database
    user_email = current_user.email

    # Get list of files uploaded by user
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], user_email)
    uploaded_files = []
    for filename in os.listdir(user_folder):
        file_path = os.path.join(user_folder, filename)
        if os.path.isfile(file_path):
            uploaded_files.append(filename)

    return render_template('dashboard.html', uploaded_files=uploaded_files)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.find(email)
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))

        error = "Invalid username or password"
        return render_template('login.html', error=error)

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Generate a new user ID
        with open('users.csv', 'r') as f:
            reader = csv.reader(f)
            user_id = str(len(list(reader)) + 1)

        # Add user to CSV file
        with open('users.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([user_id, email, password])

        # Create folder for storing files
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], email)
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        return redirect('/dashboard')
    else:
        return render_template('signup.html')



@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            email = current_user.email
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], email)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            filename = secure_filename(file.filename)
            file.save(os.path.join(folder_path, filename))
            flash('File successfully uploaded')
            return redirect(url_for('dashboard'))
    return render_template('upload.html')


@app.route('/results')
@login_required
def results():
    # Read the data from a CSV file
    file = 'data1.csv'
    user_email = current_user.email

    #filename = request.args.get('filename')
    #file = os.path.join(app.config['UPLOAD_FOLDER'], user_email,filename)

    df = pd.read_csv(file, header=None)
    df.fillna(0, inplace=True)

    # Transform DataFrame into list of transactions
    transactions = []
    for i in range(0, len(df)):
        transactions.append([str(df.values[i, j]) for j in range(0, len(df.columns)) if str(df.values[i, j]) != '0'])

    # Perform Apriori algorithm
    rules = apriori(transactions, min_support=0.003, min_confidence=0.2, min_lift=3, min_length=2)

    # Convert the results to a list of dictionaries for easier processing in the template
    results = []
    for rule in rules:
        result = {}
        result['items'] = ', '.join(rule.items)
        result['support'] = rule.support
        result['confidence'] = rule.ordered_statistics[0].confidence
        result['lift'] = rule.ordered_statistics[0].lift
        results.append(result)

    # Get the values of the 'sortby' and 'search' query parameters
    sortby = request.args.get('sortby', default=None, type=str)
    search = request.args.get('search', default=None, type=str)

    # Sort the results based on the 'sortby' parameter
    if sortby == 'support':
        results = sorted(results, key=lambda k: k['support'], reverse=True)
    elif sortby == 'confidence':
        results = sorted(results, key=lambda k: k['confidence'], reverse=True)
    elif sortby == 'lift':
        results = sorted(results, key=lambda k: k['lift'], reverse=True)

    # Search the results based on the 'search' parameter
    if search:
        results = [result for result in results if search.lower() in result['items'].lower()]
    print(results)


    # Render the template with the results
    return render_template('results.html', results=results)

@app.route('/process_data')
def process_data():
    uploads_path = os.path.join(app.root_path, 'uploads', current_user.email)
    file_list = os.listdir(uploads_path)
    files = []
    for file in file_list:
        if file.endswith('.csv'):
            name = os.path.splitext(file)[0]  # get file name without extension
            url = url_for('results', filename=file)
            files.append({'name': name, 'url': url})
    return render_template('process_data.html', files=files)



if __name__ == '__main__':
    app.run(debug=True)