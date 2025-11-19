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
            {'username':'oktavialovi4@gmail.com', 'password': 'oktavialovi4', 'email': 'oktavialovi4@gmail.com'},
            {'username':'utawabukizara77@gmail.com', 'password': 'utawabukizara77', 'email': 'utawabukizara77@gmail.com'},
            {'username':'alfiyazain27@gmail.com', 'password': 'alfiyazain27', 'email': 'alfiyazain27@gmail.com'},
            {'username':'haziqjuli@gmail.com', 'password': 'haziqjuli', 'email': 'haziqjuli@gmail.com'},
            {'username':'parhusip.kputri@gmail.com', 'password': 'parhusip.kputri', 'email': 'parhusip.kputri@gmail.com'},
            {'username':'nurakhmad@gmail.com', 'password': 'nurakhmad', 'email': 'nurakhmad@gmail.com'},
            {'username':'sorrowingwraith@gmail.com', 'password': 'sorrowingwraith', 'email': 'sorrowingwraith@gmail.com'},
            {'username':'fauzankahfi28@gmail.com', 'password': 'fauzankahfi28', 'email': 'fauzankahfi28@gmail.com'},
            {'username':'almu26zaky@gmail.com', 'password': 'almu26zaky', 'email': 'almu26zaky@gmail.com'},
            {'username':'ramandahidayat78@gmail.com', 'password': 'ramandahidayat78', 'email': 'ramandahidayat78@gmail.com'},
            {'username':'zulfa.college070503@gmail.com', 'password': 'zulfa.college070503', 'email': 'zulfa.college070503@gmail.com'},
            {'username':'luhatfim.halaf1@gmail.com', 'password': 'luhatfim.halaf1', 'email': 'luhatfim.halaf1@gmail.com'},
            {'username':'marsa.salsabila.chavila@gmail.com', 'password': 'marsa.salsabila.chavila', 'email': 'marsa.salsabila.chavila@gmail.com'},
            {'username':'perdanaignasius@gmail.com', 'password': 'perdanaignasius', 'email': 'perdanaignasius@gmail.com'},
            {'username':'ignasiusvdt@gmail.com', 'password': 'ignasiusvdt', 'email': 'ignasiusvdt@gmail.com'},
            {'username':'akbarsilalahi12@gmail.com', 'password': 'akbarsilalahi12', 'email': 'akbarsilalahi12@gmail.com'},
            {'username':'daffabarin@gmail.com', 'password': 'Daffa123!!', 'email': 'daffabarin@gmail.com'},
            {'username':'a.kinamulen@gmail.com', 'password': 'Aulia123!!', 'email': 'a.kinamulen@gmail.com'},
            {'username':'if.iqbal.fadhil@gmail.com', 'password': 'Iqbal123!!', 'email': 'if.iqbal.fadhil@gmail.com'},
            # Add more user data as needed
        ]
        for data in users_data:
            user = User.objects.create_user(**data)
            UserProfile.objects.create(user=user)
        self.stdout.write(self.style.SUCCESS('Users seeded successfully.'))
