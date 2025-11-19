from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import UserProfile, Question, Choice, UserAnswer, CorrectAnswer
from django.contrib.auth import logout
from django.shortcuts import redirect

def custom_logout(request):
    logout(request)
    return redirect('login')


@login_required
def profile(request):
    user_profile = UserProfile.objects.get(user=request.user)
    user_answers = UserAnswer.objects.filter(user=request.user)
    correct_answers = CorrectAnswer.objects.all()
    
    # Calculate the score
    score = 0
    for user_answer in user_answers:
        correct_answer = correct_answers.filter(question=user_answer.question).first()
        if correct_answer and user_answer.selected_choice == correct_answer.correct_choice:
            score += 1
    
    user_profile.score = score
    user_profile.save()

    # Check if the user has attempted the test
    test_attempted = user_answers.exists()
    
    return render(request, 'profile.html', {'user_profile': user_profile, 'score': score, 'test_attempted': test_attempted})

@login_required
def test_page(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    audio_file = question.audio_file if question.audio_file else None
    
    # Fetch choices for the question
    choices = question.choices.all()
    
    # Check if this is the first time the user accesses the test page
    if not UserAnswer.objects.filter(user=request.user).exists():
        # Retrieve the user's profile
        user_profile = UserProfile.objects.get(user=request.user)
        # Set the test_attempted flag to True
        user_profile.test_attempted = True
        user_profile.save()
    
    if request.method == 'POST':
        selected_choice_id = request.POST.get('selected_choice')
        selected_choice = get_object_or_404(Choice, pk=selected_choice_id)
        UserAnswer.objects.update_or_create(user=request.user, question=question, defaults={'selected_choice': selected_choice})
        next_question = Question.objects.filter(id__gt=question_id).order_by('id').first()
        if next_question:
            return redirect('test_page', question_id=next_question.id)
        else:
            return redirect('profile')
    
    return render(request, 'test_page.html', {'question': question, 'audio_file': audio_file, 'choices': choices})
