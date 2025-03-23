from application.database import db

# -------------------- USER MODEL --------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10), nullable=False)  # 'admin' or 'user'
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    approved = db.Column(db.Boolean, default=False)

    def serialize(self):
        return {
            "id": self.id,
            "role": self.role,
            "username": self.username,
            "email": self.email
        }

    def __repr__(self):
        return '<User %r>' % self.username


# -------------------- SUBJECT MODEL --------------------
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sub_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(500), nullable=False)

    chapters = db.relationship('Chapter', backref='subject', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        return f'<Subject {self.sub_name}>'


# -------------------- CHAPTER MODEL --------------------
class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chap_name = db.Column(db.String(255), nullable=False)
    sub_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

    quizzes = db.relationship('Quiz', backref='chapter', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        return f'<Chapter {self.chap_name}>'


# -------------------- QUIZ MODEL --------------------
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_name = db.Column(db.String(255), nullable=False)
    chap_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False) 

    questions = db.relationship('Question', backref='quiz', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        return f'<Quiz {self.quiz_name}>'


# -------------------- QUESTION MODEL --------------------
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question = db.Column(db.String(500), nullable=False)
    option_1 = db.Column(db.String(255), nullable=False)
    option_2 = db.Column(db.String(255), nullable=False)
    option_3 = db.Column(db.String(255), nullable=False)
    option_4 = db.Column(db.String(255), nullable=False)
    max_marks = db.Column(db.Integer, nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # Stores '1', '2', '3', or '4' as correct answer option

    def serialize(self):
        return {
            "id": self.id,
            "quiz_id": self.quiz_id,
            "question": self.question,
            "options": [self.option_1, self.option_2, self.option_3, self.option_4],
            "max_marks": self.max_marks,
            "correct_answer": self.correct_answer  # Include correct answer in the serialized output
        }

    def __repr__(self):
        return f'<Question {self.question}>'
    

    # -------------------- USER ANSWER MODEL --------------------
class UserAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option = db.Column(db.String(1), nullable=True)  # '1', '2', '3', or '4'
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    attempt = db.Column(db.Integer, nullable=False, default=1)  # New field

    user = db.relationship('User', backref='user_answers', lazy=True)
    question = db.relationship('Question', backref='user_answers', lazy=True)
    quiz = db.relationship('Quiz', backref='user_answers', lazy=True)

    def __repr__(self):
        return f'<UserAnswer User: {self.user_id}, Question: {self.question_id}, Answer: {self.selected_option}, Quiz: {self.quiz_id}, Attempt: {self.attempt}>'
