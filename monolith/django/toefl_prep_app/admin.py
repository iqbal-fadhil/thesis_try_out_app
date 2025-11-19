# toefl_prep_app/admin.py

from django.contrib import admin
from .models import UserProfile, Question, Choice, CorrectAnswer

admin.site.register(UserProfile)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(CorrectAnswer)
