from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Question(db.Model):
    url = db.Column(db.String(300), primary_key=True)
    question = db.Column(db.String(300), nullable=False)
    options = db.relationship('Choice', backref='question', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'url': self.url,
            'question': self.question,
            'options': [choice.to_dict() for choice in self.options]
        }

class Choice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    option = db.Column(db.String(300), nullable=False)
    votes = db.Column(db.Integer, nullable=False)
    question_url = db.Column(db.String(300), db.ForeignKey('question.url'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'option': self.option,
            'votes': self.votes
        }
