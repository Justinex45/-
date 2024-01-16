from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import json
import os
import datetime
import pandas as pd
import seaborn as sns
from flask_sqlalchemy import SQLAlchemy
import matplotlib.pyplot as plt
from classifier import classify, classify_student, create_learning_plan
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
student_df = pd.DataFrame()
video_df = pd.read_excel(r".\static\video.xlsx", dtype={'影片標題': str, '影片連結': str, '類別': str, '難易度': int})

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
class VideoSearch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)

with app.app_context():
    for index, row in video_df.iterrows():
        video_entry = VideoSearch(title=row['影片標題'],
                                  link=row['影片連結'],
                                  category=row['類別'],
                                  difficulty=row['難易度'])
        db.session.add(video_entry)
    db.session.commit()

@app.route('/save_gmail', methods=['POST'])
def save_gmail_route():
    gmail_data = request.get_json()
    gmail_text = gmail_data.get('gmail', '')
    if gmail_text:
        save_gmail(gmail_text)
    return jsonify({'message': 'Gmail saved successfully'})

def get_messages():
    messages = []
    if os.path.exists('messages.json') and os.path.getsize('messages.json') > 0:
        with open('messages.json', 'r') as file:
            messages = json.load(file)
    return messages

def save_message(message):
    messages = get_messages()
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages.append({"message": message, "time": current_time})
    with open('messages.json', 'w') as file:
        json.dump(messages, file)
        
def save_gmail(gmail):
    gmail_data = []
    if os.path.exists('gmail.json') and os.path.getsize('gmail.json') > 0:
        with open('gmail.json', 'r') as file:
            gmail_data = json.load(file)
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    gmail_data.append({"gmail": gmail, "time": current_time})
    
    with open('gmail.json', 'w') as file:
        json.dump(gmail_data, file)

    print(f"Gmail saved successfully: {gmail}")

@app.route('/get_messages')
def get_messages_route():
    messages = get_messages()
    return jsonify(messages)

@app.route('/add_message', methods=['POST'])
def add_message():
    message_data = request.get_json()
    message_text = message_data.get('message', '')
    if message_text:
        save_message(message_text)
    return jsonify({'status': 'success'})

def save_learning_record(score, learning_time, student_df):
    df = pd.read_csv(r".\static\student_data.csv")
    new_data = {'Score': pd.to_numeric(score), 'LearningTime': pd.to_numeric(learning_time)}
    new_df = pd.DataFrame(new_data, index=[0])
    df = pd.concat([df.iloc[:, 0:2], new_df], ignore_index=True)
    classify(df)
    classify_student(df)
    df['Category2'] = (df['quadrant'] - 1) * 4 + df['Category']
    learning_plan = create_learning_plan(df['Category'].values[-1])

    sns.set(style="whitegrid")
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x='LearningTime', y='Score', hue='Category', palette='viridis', data=df, alpha=0.7, s=80)
    plt.scatter(df['LearningTime'].values[-1], df['Score'].values[-1], color='red', marker='X', s=100, label='YOU')
    plt.title('Student Distribution')
    plt.xlabel('Learning Time')
    plt.ylabel('Score')
    plt.legend(title='Category', bbox_to_anchor=(1, 1), loc='upper left')
    plt.show()

    return learning_plan

@app.route('/record_learning', methods=['POST'])
def record_learning():
    global student_df
    data = request.get_json()
    score = data.get('Score')
    learning_time = data.get('LearningTime')

    learning_plan = save_learning_record(score, learning_time, student_df)

    response_message = f"成功儲存學習記錄。Score: {score}, Learning Time: {learning_time}"

    return jsonify({'message': response_message, 'learning_plan': learning_plan})

@app.route('/submit', methods=['POST'])
def submit():
    email = request.form.get('email')
    submission = Submission(email=email)
    db.session.add(submission)
    db.session.commit()
    flash('提交成功！我們將與您聯絡。')  # 暫存消息
    save_gmail(email)  # 將 email 存入 gmail.json
    return redirect(url_for('educational_resources'))  # 重定向到 'educational_resources'

@app.route('/gmail_list', methods=['GET'])
def get_gmail_list():
    gmail_data = []
    if os.path.exists('gmail.json') and os.path.getsize('gmail.json') > 0:
        with open('gmail.json', 'r') as file:
            gmail_data = json.load(file)
    return jsonify(gmail_data)

@app.route('/educational-resources.html')
def educational_resources():
    categories = video_df['類別'].unique()
    return render_template('educational-resources.html', categories=categories)

@app.route('/videos', methods=['POST'])
def get_videos():
    selected_category = request.form.get('categories')
    filtered_videos = video_df[video_df['類別'] == str(selected_category)]
    videos = [{'title': title, 'link': link, 'difficulty': difficulty} for title, link, difficulty in zip(filtered_videos['影片標題'], filtered_videos['影片連結'], filtered_videos['難易度'])]
    
    return jsonify({'videos': videos})
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/index.html', endpoint='index_page')
def home():
    return render_template('index.html')
@app.route('/individual-learning.html')
def individual_learning():
    return render_template('individual-learning.html')

@app.route('/community.html')
def community():
    return render_template('community.html')

@app.route('/about-us.html')
def about_us():
    return render_template('about-us.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
