from flask import Flask, request, render_template, make_response, jsonify
from bs4 import BeautifulSoup
import requests
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .models.choices import db, Question, Choice
import re
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

client = OpenAI()

DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
DATABASE_SERVER = os.getenv('DATABASE_SERVER')
DATABASE_PORT = os.getenv('DATABASE_PORT')
DATABASE_NAME = os.getenv('DATABASE_NAME')

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_SERVER}:{DATABASE_PORT}/{DATABASE_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

migrate = Migrate(app, db)

with app.app_context():
    db.create_all()

@app.route('/api/scrape', methods=['POST'])
def scrape():
    url = request.json['url']

    existing_question = Question.query.filter_by(url=url).first()

    if existing_question:
        return jsonify({'data': existing_question.to_dict()}), 200
    else:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        links = [a['href'] for a in soup.find_all('a', href=True)]
        
        def generate():
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Simplify this information down to a multiple choice question about why a user would be visiting this website as if the quest was being asked directly to the user and give exactly four specific options and all of the above cannot be one of them. Separate the options using a number followed by a .: " + text + str(links)}]
            )

            return stream.choices[0].message.content

        output = generate()

        lines = output.splitlines()
        question = lines[0]
        choices = []

        for line in lines[1:]:
            match = re.match(r'^[A-Za-z0-9][.)]\s*(.*)', line)

            if match:
                choices.append(match.group(1).strip())

        newQuestion = Question(url=url, question=question)
        options = [
            Choice(option=choices[0], votes=0, question_url=newQuestion.url),
            Choice(option=choices[1], votes=0, question_url=newQuestion.url),
            Choice(option=choices[2], votes=0, question_url=newQuestion.url),
            Choice(option=choices[3], votes=0, question_url=newQuestion.url),
        ]

        db.session.add(newQuestion)

        for option in options:
            db.session.add(option)

        try:
            db.session.commit()

            data = Question.query.filter_by(url=url).first()    

            return jsonify({'data': data.to_dict()}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

@app.route('/api/vote', methods=['POST'])
def vote():
    optionID = request.json['id']

    choice = Choice.query.filter_by(id=optionID).first()
    choice.votes += 1

    try:
        db.session.commit()

        data = Question.query.filter_by(url=choice.question_url).first()

        return jsonify({'data': data.to_dict()}), 200
    except:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)