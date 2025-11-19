from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from toefl_prep_app.models import UserProfile

class Command(BaseCommand):
    help = 'Seed user data'

    def handle(self, *args, **kwargs):
        # Check if there are existing users
        # if User.objects.exists():
        #     self.stdout.write(self.style.WARNING('Users already exist. Aborting...'))
        #     return

        # Create users and associated user profiles
        self.stdout.write('Seeding users...')
        users_data = [
            {'username':'daffabarin@gmail.com', 'password': 'Daffa123!!', 'email': 'daffabarin@gmail.com'},
            {'username':'a.kinamulen@gmail.com', 'password': 'Aulia123!!', 'email': 'a.kinamulen@gmail.com'},
            # Add more user data as needed
        ]
        for data in users_data:
            user = User.objects.create_user(**data)
            UserProfile.objects.create(user=user)
        self.stdout.write(self.style.SUCCESS('Users seeded successfully.'))
