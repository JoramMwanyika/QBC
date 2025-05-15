from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, session
from sqlalchemy import func
import json
from . import db
from .models import Subject, Chapter, Quiz, Question, Score, User
from .decorators import admin_required, user_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

views = Blueprint("views", __name__)

@views.route("/", methods=["GET"])
def landing_page():
    return render_template("landing_page.html", user=current_user)

@views.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("views.admin_dashboard"))
    return redirect(url_for("views.user_dashboard"))

#user admin page
@views.route("/user-about")
@login_required
def user_about():
    return render_template("user/about.html")

#admin about page
@views.route("/admin-about")
@login_required
@admin_required
def admin_about():
    return render_template("admin/about.html")

@views.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    subjects = Subject.query.all()
    return render_template("admin/dashboard.html", subjects=subjects)

@views.route("/admin/delete_subject/<int:subject_id>", methods=["POST"])
@login_required
@admin_required
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash("Subject deleted successfully.", "success")
    return redirect(url_for("views.admin_dashboard"))

@views.route("/admin/delete_chapter/<int:chapter_id>", methods=["POST"])
@login_required
@admin_required
def delete_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    subject_id = chapter.subject_id  # Save subject_id before deletion
    db.session.delete(chapter)
    db.session.commit()
    flash("Chapter deleted successfully.", "success")
    return redirect(url_for("views.view_chapters", subject_id=subject_id))

@views.route("/admin/add_subject", methods=["GET", "POST"])
@login_required
@admin_required
def add_subject():
    if request.method == "POST":
        name = request.form.get("name", "").strip().lower()  # Convert to lowercase
        description = request.form.get("description", "").strip()
        qualification = request.form.get("qualification", "").strip()

        # Check for case-insensitive duplicate
        if Subject.query.filter(db.func.lower(Subject.name) == name).first():
            flash("Subject already exists!", "error")
        else:
            new_subject = Subject(name=name, description=description, qualification=qualification)
            db.session.add(new_subject)
            db.session.commit()
            flash("Subject added successfully!", "success")

        return redirect(url_for("views.admin_dashboard"))

    return render_template("subjects_chapters/add_subject.html")

@views.route("/admin/chapters/<int:subject_id>")
@login_required
@admin_required
def view_chapters(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    chapters = Chapter.query.filter_by(subject_id=subject_id).all()
    
    return render_template("subjects_chapters/view_chapters.html", subject=subject, chapters=chapters)

@views.route("/admin/add_chapter/<int:subject_id>", methods=["GET", "POST"])
@login_required
@admin_required
def add_chapter(subject_id):
    subject = Subject.query.get_or_404(subject_id)

    if request.method == "POST":
        name = request.form.get("name").strip()
        description = request.form.get("description").strip()

        new_chapter = Chapter(name=name, description=description, subject_id=subject.id)
        db.session.add(new_chapter)
        db.session.commit()
        flash("Chapter added successfully!", "success")
        return redirect(url_for("views.view_chapters", subject_id=subject.id))  

    return render_template("subjects_chapters/add_chapter.html", subject=subject)

@views.route("/admin/quiz/<int:quiz_id>", methods=["GET", "POST"])
@login_required
@admin_required
def view_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz.id).all()

    if request.method == "POST":
        question_text = request.form.get("question_text")  # Ensure this matches the model field name
        option_a = request.form.get("option_a")
        option_b = request.form.get("option_b")
        option_c = request.form.get("option_c")
        option_d = request.form.get("option_d")
        correct_option = request.form.get("correct_option")

        new_question = Question(
            quiz_id=quiz.id,
            question_text=question_text,  # Use the correct column name
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct_option,
        )
        db.session.add(new_question)
        db.session.commit()
        flash("Question added successfully!", "success")
        return redirect(url_for("views.view_quiz", quiz_id=quiz.id))

    return render_template("quizzes/view_quiz.html", quiz=quiz, questions=questions)

@views.route("/admin/add_quiz/<int:chapter_id>", methods=["GET", "POST"])
@login_required
@admin_required
def add_quiz(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)

    if request.method == "POST":
        try:
            time_duration = int(request.form.get("time_duration"))
            remarks = request.form.get("remarks").strip()

            new_quiz = Quiz(chapter_id=chapter.id, time_duration=time_duration, remarks=remarks)
            db.session.add(new_quiz)
            db.session.commit()
            flash("Quiz added successfully!", "success")
            return redirect(url_for("views.view_quizzes", chapter_id=chapter.id))
        except ValueError:
            flash("Time duration must be a valid number!", "error")

    return render_template("quizzes/add_quiz.html", chapter=chapter)

@views.route("/admin/view_quizzes/<int:chapter_id>")
@login_required
@admin_required
def view_quizzes(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()
    return render_template("quizzes/view_quizzes.html", chapter=chapter, quizzes=quizzes)

@views.route("/admin/delete_quiz/<int:quiz_id>", methods=["POST"])
@login_required
@admin_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    chapter_id = quiz.chapter_id  # Store chapter ID before deleting
    db.session.delete(quiz)
    db.session.commit()
    flash("Quiz deleted successfully.", "success")
    return redirect(url_for("views.view_quizzes", chapter_id=chapter_id))

@views.route("/admin/edit_question/<int:quiz_id>/<int:question_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_question(quiz_id, question_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    question = Question.query.get_or_404(question_id)

    if request.method == "POST":
        question.question_text = request.form["question_text"]
        question.option_a = request.form["option_a"]
        question.option_b = request.form["option_b"]
        question.option_c = request.form["option_c"]
        question.option_d = request.form["option_d"]
        question.correct_option = request.form["correct_option"]
        db.session.commit()
        flash("Question updated successfully!", "success")
        return redirect(url_for("views.view_quiz", quiz_id=quiz.id))

    return render_template("quizzes/edit_question.html", quiz=quiz, question=question)

@views.route("/admin/delete_question/<int:question_id>", methods=["POST"])
@login_required
@admin_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_id = question.quiz_id  # Store quiz ID before deleting
    db.session.delete(question)
    db.session.commit()
    flash("Question deleted successfully!", "danger")
    return redirect(url_for("views.view_quiz", quiz_id=quiz_id))

@views.route("/admin/analytics")
@login_required
@admin_required
def admin_analytics():
    return render_template('admin/analytics.html')

@views.route('/admin/analytics/data')
@login_required
@admin_required
def admin_analytics_data():
    # Exclude admins from student count
    total_students = User.query.filter_by(is_admin=False).count()
    
    total_subjects = Subject.query.count()
    total_quizzes = Quiz.query.count()
    active_quizzes = Quiz.query.filter_by(published=True).count()

    # Subject Performance (Average Scores Per Subject, Excluding Admins)
    subject_performance = db.session.query(
        Subject.name, func.coalesce(func.avg(Score.total_score), 0)
    ).join(Chapter).join(Quiz).outerjoin(Score).join(User).filter(User.is_admin == False) \
    .group_by(Subject.id).all()

    # Convert to dictionary format
    subject_performance_data = [
        {"subject": subject, "avg_score": avg_score}
        for subject, avg_score in subject_performance
    ]

    # Qualification Distribution (Excluding Admins)
    qualification_distribution = db.session.query(
        User.qualification, func.count(User.id)
    ).filter(User.is_admin == False).group_by(User.qualification).all()

    qualification_distribution_data = [
        {"qualification": qual, "count": count}
        for qual, count in qualification_distribution
    ]

    return jsonify({
        "total_students": total_students,
        "total_subjects": total_subjects,
        "total_quizzes": total_quizzes,
        "active_quizzes": active_quizzes,
        "subject_performance": subject_performance_data,
        "qualification_distribution": qualification_distribution_data
    })

@views.route('/admin/quiz/<int:quiz_id>/toggle_publish', methods=['POST'])
@login_required
@admin_required
def toggle_publish(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    quiz.published = not quiz.published
    db.session.commit()
    status = "published" if quiz.published else "unpublished"
    flash(f"Quiz {status} successfully!", "success")
    return redirect(url_for("views.view_quizzes", chapter_id=quiz.chapter_id))

@views.route("/user")
@login_required
@user_required
def user_dashboard():
    # Get all subjects that match the user's qualification
    subjects = Subject.query.filter_by(qualification=current_user.qualification).all()
    
    # For each subject, get its chapters and quizzes
    subject_data = []
    for subject in subjects:
        chapters = Chapter.query.filter_by(subject_id=subject.id).all()
        chapter_data = []
        
        for chapter in chapters:
            quizzes = Quiz.query.filter_by(chapter_id=chapter.id, published=True).all()
            quiz_data = []
            
            for quiz in quizzes:
                # Check if user has already taken this quiz
                score = Score.query.filter_by(user_id=current_user.id, quiz_id=quiz.id).first()
                quiz_data.append({
                    'id': quiz.id,
                    'time_duration': quiz.time_duration,
                    'remarks': quiz.remarks,
                    'score': score.total_score if score else None,
                    'taken': score is not None
                })
            
            chapter_data.append({
                'id': chapter.id,
                'name': chapter.name,
                'description': chapter.description,
                'quizzes': quiz_data
            })
        
        subject_data.append({
            'id': subject.id,
            'name': subject.name,
            'description': subject.description,
            'chapters': chapter_data
        })
    
    return render_template("user/dashboard.html", subjects=subject_data)

@views.route("/user/quiz/<int:quiz_id>", methods=["GET"])
@login_required
@user_required
def start_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check if quiz is published
    if not quiz.published:
        flash("This quiz is not available yet.", "error")
        return redirect(url_for("views.user_dashboard"))
    
    # Check if user has already taken this quiz
    existing_score = Score.query.filter_by(user_id=current_user.id, quiz_id=quiz.id).first()
    if existing_score:
        flash("You have already taken this quiz.", "error")
        return redirect(url_for("views.user_dashboard"))
    
    # Get all questions for this quiz
    questions = Question.query.filter_by(quiz_id=quiz.id).all()
    
    if not questions:
        flash("This quiz has no questions yet.", "error")
        return redirect(url_for("views.user_dashboard"))
    
    return render_template(
        "quizzes/take_quiz.html",
        quiz=quiz,
        questions=questions,
        time_duration=quiz.time_duration
    )

@views.route('/user/analytics')
@login_required
@user_required
def user_analytics():
    return render_template('user/analytics.html')

@views.route('/user/analytics/data')
@login_required
@user_required
def user_analytics_data():
    # Get all scores for the current user
    scores = Score.query.filter_by(user_id=current_user.id).all()
    
    # Calculate total quizzes taken
    total_quizzes = len(scores)
    
    # Calculate average score
    avg_score = sum(score.total_score for score in scores) / total_quizzes if total_quizzes > 0 else 0
    
    # Get subject-wise performance
    subject_performance = db.session.query(
        Subject.name,
        func.avg(Score.total_score).label('avg_score')
    ).join(Chapter).join(Quiz).join(Score).filter(
        Score.user_id == current_user.id
    ).group_by(Subject.id).all()
    
    subject_data = [
        {"subject": subject, "avg_score": avg_score}
        for subject, avg_score in subject_performance
    ]
    
    return jsonify({
        "total_quizzes": total_quizzes,
        "average_score": avg_score,
        "subject_performance": subject_data
    })

@views.route("/user/quiz/submit", methods=["POST"])
@login_required
@user_required
def submit_quiz():
    data = request.get_json()
    quiz_id = data.get('quiz_id')
    answers = data.get('answers', {})
    
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    total_questions = len(questions)
    correct_answers = 0
    
    for question in questions:
        user_answer = answers.get(str(question.id))
        if user_answer == question.correct_option:
            correct_answers += 1
    
    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
    
    # Save the score
    new_score = Score(
        user_id=current_user.id,
        quiz_id=quiz_id,
        total_score=score,
        total_questions=total_questions,
        correct_answers=correct_answers
    )
    db.session.add(new_score)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "score": score,
        "total_questions": total_questions,
        "correct_answers": correct_answers
    })

@views.route("/user/quiz/performance/<int:quiz_id>")
@login_required
@user_required
def view_performance(quiz_id):
    score = Score.query.filter_by(user_id=current_user.id, quiz_id=quiz_id).first_or_404()
    quiz = Quiz.query.get_or_404(quiz_id)
    
    return render_template(
        "user/performance.html",
        score=score,
        quiz=quiz
    )

@views.route("/profile")
@login_required
def profile():
    return render_template("user/profile.html")

@views.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        
        # Check if email is already taken by another user
        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            flash("Email already taken!", "error")
            return redirect(url_for("views.edit_profile"))
        
        current_user.full_name = full_name
        current_user.email = email
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("views.profile"))
    
    return render_template("user/edit_profile.html")

@views.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        if not check_password_hash(current_user.password, current_password):
            flash("Current password is incorrect!", "error")
        elif new_password != confirm_password:
            flash("New passwords don't match!", "error")
        elif len(new_password) < 8:
            flash("Password must be at least 8 characters long!", "error")
        else:
            current_user.password = generate_password_hash(new_password)
            db.session.commit()
            flash("Password changed successfully!", "success")
            return redirect(url_for("views.profile"))
    
    return render_template("user/change_password.html")

@views.route("/admin/profile")
@login_required
@admin_required
def admin_profile():
    return render_template("admin/profile.html")

@views.route("/admin/profile/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_admin_profile():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        
        # Check if email is already taken by another user
        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            flash("Email already taken!", "error")
            return redirect(url_for("views.edit_admin_profile"))
        
        current_user.full_name = full_name
        current_user.email = email
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("views.admin_profile"))
    
    return render_template("admin/edit_profile.html")

@views.route('/admin/change/password', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        if not check_password_hash(current_user.password, current_password):
            flash("Current password is incorrect!", "error")
        elif new_password != confirm_password:
            flash("New passwords don't match!", "error")
        elif len(new_password) < 8:
            flash("Password must be at least 8 characters long!", "error")
        else:
            current_user.password = generate_password_hash(new_password)
            db.session.commit()
            flash("Password changed successfully!", "success")
            return redirect(url_for("views.admin_profile"))
    
    return render_template("admin/change_password.html")

@views.route('/set-language/<lang>')
def set_language(lang):
    if lang in ['en', 'sw']:
        session['language'] = lang
    return redirect(request.referrer or url_for('views.landing_page'))
