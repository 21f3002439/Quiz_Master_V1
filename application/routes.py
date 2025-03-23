from flask import jsonify, render_template, request, redirect, url_for, session, flash
from application.models import Chapter, Quiz, User, Subject, Question, UserAnswer
from application.database import db
from app import app
import numpy as np



# -------------------- ROLE-BASED DASHBOARD --------------------
@app.route('/')
def index():
    if 'user_id' in session:
        if session['user_role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return render_template('index.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash('You must log in first.', 'warning')
        return redirect(url_for('login'))
    
    subjects = Subject.query.all()
    return render_template('admin_dashboard.html', subjects=subjects)

@app.route('/user-dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('user_role') != 'user':
        flash('You must log in first.', 'warning')
        return redirect(url_for('login'))

    # Fetch all subjects and their corresponding chapters
    subjects = Subject.query.all()

    # Pass the subjects to the template
    return render_template('user_dashboard.html', subjects=subjects)


# -------------------- LOGIN --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:  
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            if user.email == 'admin@gmail.com':
                session['user_id'] = user.id
                session['user_email'] = user.email
                session['user_role'] = user.role  # Admin 
                return redirect(url_for('admin_dashboard'))
            
            if not user.approved:
                flash('Wait for admin approval', 'warning')
                return redirect(url_for('login')) 
            
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_role'] = user.role  # Admin or User

            flash('Login successful!', 'success')
            return redirect(url_for('index'))

        flash('Incorrect email or password', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')

# -------------------- REGISTER --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['name']
        email = request.form['email']
        password = request.form['password']
        # role = 'admin' if email == 'admin@gmail.com' else 'user'
        role = 'user'

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists', 'danger')
            return redirect(url_for('register'))

        user = User(username=username, email=email, password=password, role=role)
        db.session.add(user)
        db.session.commit() 
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# -------------------- APPROVE USER --------------------
@app.route('/approve_user/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    print(user)

    if user.email == 'admin@gmail.com':
        flash("Admin cannot approve or reject their own account.", "danger")
        return redirect(url_for('exam_summary'))
    
    # if user.approved:
    #     flash("User is already approved.", "info")
    #     return redirect(url_for('exam_summary'))  # Redirect to the summary page
    
    user.approved = True  # Mark the user as approved
    db.session.commit()
    flash("User approved successfully", "success")
    return redirect(url_for('exam_summary'))  # Redirect to the summary page



# -------------------- REJECT USER --------------------
@app.route('/reject_user/<int:user_id>', methods=['POST'])
def reject_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.email == 'admin@gmail.com':
        flash("Admin cannot approve or reject their own account.", "danger")
        return redirect(url_for('exam_summary')) 
    
    # Delete all user answers before deleting the user to avoid integrity errors
    user_answers = UserAnswer.query.filter_by(user_id=user_id).all()
    for answer in user_answers:
        db.session.delete(answer)  # Delete each user answer
    
    db.session.commit()  # Commit the deletion of user answers

    # Now, delete the user
    db.session.delete(user)
    db.session.commit()
    
    flash("User rejected and deleted successfully", "danger")
    return redirect(url_for('exam_summary'))  # Redirect to the summary page




# -------------------- LOGOUT --------------------
@app.route('/logout')
def logout():
    session.clear()  
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))



# -------------------- ADD SUBJECT --------------------
@app.route('/add_subject', methods=['POST'])
def add_subject():
    subject_name = request.form['subject_name']
    description = request.form['description']
    
    new_subject = Subject(sub_name=subject_name, description=description)
    db.session.add(new_subject)
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))



# -------------------- EDIT SUBJECT --------------------
@app.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    if request.method == 'POST':
        subject.sub_name = request.form['subject_name']
        subject.description = request.form['description']
        db.session.commit()
        flash('Subject updated successfully!', 'success')  # Flash message
        return redirect(url_for('admin_dashboard'))
    
    return render_template('edit_subject.html', subject=subject)



# -------------------- DELETE SUBJECT --------------------
@app.route('/delete_subject/<int:subject_id>', methods=['GET'])
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)

    # Step 1: Get all questions related to this subject
    questions = Question.query.join(Quiz).join(Chapter).filter(Chapter.sub_id == subject_id).all()

    # Step 2: Delete all UserAnswer records related to these questions
    for question in questions:
        UserAnswer.query.filter_by(question_id=question.id).delete()

    # Step 3: Now delete the subject (which will also delete its chapters, quizzes, and questions)
    db.session.delete(subject)

    try:
        db.session.commit()
        flash('Subject deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting subject: {str(e)}', 'danger')

    return redirect(url_for('admin_dashboard'))


# -------------------- ADD CHAPTER --------------------
@app.route('/add_chapter/<int:subject_id>', methods=['GET', 'POST'])
def add_chapter(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    if request.method == 'POST':
        chapter_name = request.form['chapter_name']
        new_chapter = Chapter(chap_name=chapter_name, sub_id=subject_id)
        db.session.add(new_chapter)
        db.session.commit()
        return redirect(url_for('add_chapter', subject_id=subject_id))  

    return render_template('add_chapter.html', subject=subject)

# -------------------- DELETE CHAPTER --------------------
@app.route('/delete_chapter/<int:chapter_id>', methods=['GET'])
def delete_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    subject = chapter.subject  # Get the related subject for the chapter
    db.session.delete(chapter)
    db.session.commit()
    return render_template('add_chapter.html', subject=subject)  # Pass the subject to the template



# -------------------- EDIT CHAPTER --------------------
@app.route('/edit_chapter/<int:chapter_id>', methods=['GET', 'POST'])
def edit_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)

    if request.method == 'POST':
        chapter.chap_name = request.form['chapter_name']
        db.session.commit()  # Commit the changes to the database
        flash('Chapter updated successfully!', 'success')  # Flash message
        return redirect(url_for('add_chapter', subject_id=chapter.subject.id))  # Redirect back to add chapter page

    # If GET request, render the page with the current chapter information
    return render_template('edit_chapter.html', chapter=chapter)






# -------------------- ADD QUESTION --------------------
@app.route('/add_question/<int:quiz_id>', methods=['GET', 'POST'])
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    chapter = Chapter.query.get_or_404(quiz.chap_id)  # Ensure we fetch the chapter
    questions = Question.query.filter_by(quiz_id=quiz.id).all()

    if request.method == 'POST':
        question_text = request.form['question']
        option_1 = request.form['option_1']
        option_2 = request.form['option_2']
        option_3 = request.form['option_3']
        option_4 = request.form['option_4']
        max_marks = int(request.form['max_marks'])
        correct_answer = request.form['correct_answer']

        new_question = Question(
            quiz_id=quiz.id,
            question=question_text,
            option_1=option_1,
            option_2=option_2,
            option_3=option_3,
            option_4=option_4,
            max_marks=max_marks,
            correct_answer=correct_answer
        )
        db.session.add(new_question)
        db.session.commit()
        flash('Question added successfully!', 'success')

        # ✅ Redirect to avoid form resubmission issue
        return redirect(url_for('add_question', quiz_id=quiz.id))

    return render_template('add_question.html', quiz=quiz, chapter=chapter, questions=questions)





# -------------------- EDIT QUESTION --------------------
@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)

    if request.method == 'POST':
        question.question = request.form['question']
        question.option_1 = request.form['option_1']
        question.option_2 = request.form['option_2']
        question.option_3 = request.form['option_3']
        question.option_4 = request.form['option_4']
        question.max_marks = int(request.form['max_marks'])
        question.correct_answer = request.form['correct_answer']
        
        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('add_question', quiz_id=question.quiz_id))
    
    return render_template('edit_question.html', question=question)


# -------------------- DELETE QUESTION --------------------
@app.route('/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    
    db.session.delete(question)
    db.session.commit()
    
    flash('Question deleted successfully!', 'success')
    return redirect(request.referrer or url_for('add_question', quiz_id=question.quiz_id))





# -------------------- CREATE QUIZ --------------------
@app.route('/create_quiz/<int:chapter_id>', methods=['GET', 'POST'])
def create_quiz(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)

    if request.method == 'POST':
        quiz_name = request.form['quiz_name']

        # Check if a quiz already exists for this chapter
        existing_quiz = Quiz.query.filter_by(chap_id=chapter.id).first()
        if existing_quiz:
            flash("A quiz for this chapter already exists.", "warning")
            return redirect(url_for('admin_dashboard'))

        # Create new quiz
        new_quiz = Quiz(quiz_name=quiz_name, chap_id=chapter.id)
        db.session.add(new_quiz)
        db.session.commit()

        flash('Quiz created successfully!', 'success')
        return redirect(url_for('add_question', chapter_id=chapter.id))

    return render_template('create_quiz.html', chapter=chapter)




# -------------------- ADD QUIZ --------------------
@app.route('/add_quiz/<int:chapter_id>', methods=['GET', 'POST'])
def add_quiz(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    previous_quizzes = Quiz.query.filter_by(chap_id=chapter_id).all()

    if request.method == 'POST':
        quiz_name = request.form['title']
        scheduled_date = request.form['scheduled_date']

        # Get the duration in HH:MM format from the form
        duration = request.form['duration']  # e.g., '02:30'

        try:
            # Split the duration string into hours and minutes
            duration_hours, duration_minutes = map(int, duration.split(':'))

            # Convert total duration into minutes
            total_duration = (duration_hours * 60) + duration_minutes
        except ValueError:
            # If the duration format is invalid, return an error message
            return "Invalid duration format. Please use HH:MM format.", 400

        # Create the new quiz with the calculated duration in minutes
        new_quiz = Quiz(quiz_name=quiz_name, chap_id=chapter.id, duration_minutes=total_duration)
        db.session.add(new_quiz)
        db.session.commit()

        # Redirect to add_question page for the newly created quiz
        return redirect(url_for('add_question', quiz_id=new_quiz.id))  

    return render_template('add_quiz.html', chapter=chapter, previous_quizzes=previous_quizzes)


# -------------------- DELETE QUIZ --------------------
@app.route('/delete_quiz/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    # Fetch the quiz from the database
    quiz = Quiz.query.get(quiz_id)
    
    if quiz:
        # Get the chapter_id from the quiz
        chapter_id = quiz.chap_id
        
        # Delete the quiz (and its related questions due to cascade)
        db.session.delete(quiz)
        db.session.commit()

        # Redirect to the add_quiz page, passing the chapter_id
        return redirect(url_for('add_quiz', chapter_id=chapter_id))
    else:
        # In case the quiz is not found, just redirect back without deletion
        return redirect(url_for('add_quiz', chapter_id=quiz.chap_id))


# -------------------- EDIT QUIZ --------------------
@app.route('/edit_quiz/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)  # Get the quiz from the database

    if request.method == 'POST':
        # Update the quiz name from the form
        quiz.quiz_name = request.form['quiz_name']
        
        # Commit the change to the database
        db.session.commit()
        
        # Redirect to the page that shows quizzes
        return redirect(url_for('add_quiz', chapter_id=quiz.chap_id))

    return render_template('edit_quiz.html', quiz=quiz)




# -------------------- START EXAM --------------------
@app.route('/start_exam', methods=['POST'])
def start_exam():
    if 'user_id' not in session:
        flash("You must be logged in to start the exam.", "danger")
        return redirect(url_for('login'))

    subject_id = request.form.get('subject')
    chapter_id = request.form.get('chapter')
    quiz_id = request.form.get('quiz')

    if not subject_id or not chapter_id or not quiz_id:
        flash("Please select subject, chapter, and quiz.", 'warning')
        return redirect(url_for('user_dashboard'))

    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        flash("No quiz available for this selection.", "warning")
        return redirect(url_for('user_dashboard'))

    return redirect(url_for('exam_page', quiz_id=quiz.id))  # Redirect to exam page


# -------------------- GET CHAPTERS --------------------
@app.route('/get_chapters/<int:subject_id>', methods=['GET'])
def get_chapters(subject_id):
    # Fetch the chapters related to the selected subject
    chapters = Chapter.query.filter_by(sub_id=subject_id).all()
    
    # Create a response that sends chapters in JSON format
    return jsonify({
        'chapters': [{'id': chapter.id, 'chap_name': chapter.chap_name} for chapter in chapters]
    })


# -------------------- GET QUIZZES --------------------
@app.route('/get_quizzes/<int:chapter_id>', methods=['GET'])
def get_quizzes(chapter_id):
    # Fetch the quizzes related to the selected chapter
    quizzes = Quiz.query.filter_by(chap_id=chapter_id).all()

    # Create a response that sends quizzes in JSON format
    return jsonify({
        'quizzes': [{'id': quiz.id, 'quiz_name': quiz.quiz_name} for quiz in quizzes]
    })



# -------------------- EXAM PAGE --------------------
@app.route('/exam/<int:quiz_id>', methods=['GET'])
def exam_page(quiz_id):
    if 'user_id' not in session:
        flash("You must be logged in to start the exam.", "danger")
        return redirect(url_for('login'))

    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz.id).all()

    if not questions:
        flash("No questions have been added to this quiz yet.", "warning")
        return redirect(url_for('user_dashboard'))

    return render_template('start_exam.html', exam_id=quiz.id, questions=questions)



# -------------------- SUBMIT QUIZ --------------------
@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    if 'user_id' not in session:
        flash("You must be logged in to submit the exam.", "danger")
        return redirect(url_for('login'))

    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz.id).all()

    if not questions:
        flash("No questions found for this quiz.", "warning")
        return redirect(url_for('user_dashboard'))

    user_id = session['user_id']

    # Determine the current attempt number for this quiz
    last_attempt = db.session.query(db.func.max(UserAnswer.attempt)).filter_by(user_id=user_id, quiz_id=quiz.id).scalar() or 0
    new_attempt = last_attempt + 1

    correct_answers = 0
    total_marks = 0

    # Process each question and assign the new attempt number
    for question in questions:
        selected_option = request.form.get(f'question_{question.id}')
        
        user_answer = UserAnswer(
            user_id=user_id, 
            question_id=question.id, 
            selected_option=selected_option, 
            quiz_id=quiz.id,
            attempt=new_attempt
        )
        db.session.add(user_answer)

        # Check if the answer is correct and update the marks
        if selected_option and int(selected_option) == int(question.correct_answer):
            correct_answers += 1
            total_marks += question.max_marks

    db.session.commit()

    flash(f'You got {correct_answers} out of {len(questions)} correct! Total Marks: {total_marks}', 'success')
    return redirect(url_for('user_dashboard'))




# -------------------- EXAM SUMMARY --------------------
@app.route('/exam_summary')
def exam_summary():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('login'))

    # Fetch Total Users
    total_users = User.query.count() - 1  # Exclude the admin or system user if needed

    # Fetch all users
    users = User.query.all()

    # Fetch new users awaiting approval
    new_users = [user for user in users if not user.approved]  # Users awaiting approval

    # Render the template without the mean score calculation
    return render_template('exam_summary.html', 
                           total_users=total_users,
                           new_users=new_users,
                           users=users)


# -------------------- APPROVED USERS --------------------
@app.route('/approved_users')
def approved_users():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('login'))

    # Fetch all approved users
    approved_users = User.query.filter_by(approved=True).all()

    return render_template('approved_users.html', users=approved_users)


# -------------------- USER DETAILS --------------------
@app.route('/user_details/<int:user_id>')
def user_details(user_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)
    user_answers = UserAnswer.query.filter_by(user_id=user_id).all()

    if not user_answers:
        flash("No quiz attempts made by this user.", "info")
        return redirect(url_for('approved_users'))

    quiz_statistics = {}
    
    for answer in user_answers:
        question = Question.query.get(answer.question_id)
        quiz = Quiz.query.get(question.quiz_id)
        chapter = Chapter.query.get(quiz.chap_id)
        subject = Subject.query.get(chapter.sub_id)

        # Create a composite key using quiz id and attempt number
        key = (quiz.id, answer.attempt)
        if key not in quiz_statistics:
            quiz_statistics[key] = {
                'subject_name': subject.sub_name,
                'chapter_name': chapter.chap_name,
                'quiz_name': quiz.quiz_name,
                'attempt': answer.attempt,
                'total_marks': 0,
                'marks': 0
            }

        # Calculate marks for this specific attempt
        if answer.selected_option == question.correct_answer:
            quiz_statistics[key]['marks'] += question.max_marks
        quiz_statistics[key]['total_marks'] += question.max_marks

    return render_template('user_details.html', 
                         user=user, 
                         quiz_statistics=quiz_statistics)


# -------------------- USER SUMMARY --------------------
@app.route('/user_summary')
def user_summary():
    if 'user_id' not in session:
        flash("You must be logged in to view your test summary.", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get_or_404(user_id)

    user_answers = UserAnswer.query.filter_by(user_id=user_id).all()
    if not user_answers:
        flash("No quiz attempts made by this user.", "info")
        return redirect(url_for('user_dashboard'))

    # Group results by quiz id and attempt number
    quiz_statistics = {}
    total_marks_obtained = 0
    total_max_marks = 0
    total_attempts = 0

    for answer in user_answers:
        question = Question.query.get(answer.question_id)
        quiz = Quiz.query.get(question.quiz_id)
        chapter = Chapter.query.get(quiz.chap_id)
        subject = Subject.query.get(chapter.sub_id)

        # Create a composite key using quiz id and attempt number
        key = (quiz.id, answer.attempt)
        if key not in quiz_statistics:
            quiz_statistics[key] = {
                'subject_name': subject.sub_name,
                'chapter_name': chapter.chap_name,
                'quiz_name': quiz.quiz_name,
                'attempt': answer.attempt,
                'total_marks': 0,
                'marks': 0
            }

        # Calculate score for this question within the specific attempt
        if answer.selected_option == question.correct_answer:
            quiz_statistics[key]['marks'] += question.max_marks
        quiz_statistics[key]['total_marks'] += question.max_marks

    # Optionally, calculate overall totals over all attempts if needed
    for stats in quiz_statistics.values():
        total_marks_obtained += stats['marks']
        total_max_marks += stats['total_marks']
        total_attempts += 1

    total_marks_percentage = (total_marks_obtained / total_max_marks) * 100 if total_max_marks else 0

    return render_template('user_summary.html', user=user, quiz_statistics=quiz_statistics,
                           total_marks_obtained=total_marks_obtained, total_max_marks=total_max_marks,
                           total_attempts=total_attempts, total_marks_percentage=total_marks_percentage)
