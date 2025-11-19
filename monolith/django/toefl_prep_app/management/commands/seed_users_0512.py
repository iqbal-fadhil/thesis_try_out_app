from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from toefl_prep_app.models import UserProfile

class Command(BaseCommand):
    help = 'Seed user data'

    def handle(self, *args, **kwargs):
        # Optional: Uncomment the following lines if you want to abort seeding if users already exist
        # if User.objects.exists():
        #     self.stdout.write(self.style.WARNING('Users already exist. Aborting...'))
        #     return

        self.stdout.write('Seeding users...')
        users_data = [
            {'username': 'rafie7498@gmail.com', 'password': 'rafie7498', 'email': 'rafie7498@gmail.com'},
            {'username': 'wandreas886@gmail.com', 'password': 'wandreas886', 'email': 'wandreas886@gmail.com'},
            {'username': 'dhaifanazhar@gmail.com', 'password': 'dhaifanazhar', 'email': 'dhaifanazhar@gmail.com'},
            {'username': 'andregt.project@gmail.com', 'password': 'andregt.project', 'email': 'andregt.project@gmail.com'},            
        ]

        for data in users_data:
            # Create user and associated profile
            user, created = User.objects.get_or_create(username=data['username'], email=data['email'])
            if created:
                user.set_password(data['password'])
                user.save()
                UserProfile.objects.create(user=user)
                self.stdout.write(self.style.SUCCESS(f"User {data['username']} created."))
            else:
                self.stdout.write(self.style.WARNING(f"User {data['username']} already exists."))

        self.stdout.write(self.style.SUCCESS('Users seeded successfully.'))
