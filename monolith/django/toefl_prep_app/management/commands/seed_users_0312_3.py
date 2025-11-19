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
            {'username': 'sridamai@student.telkomuniversity.ac.id', 'password': 'sridamai', 'email': 'sridamai@student.telkomuniversity.ac.id'},
            {'username': 'fauziachmad1405@gmail.com', 'password': 'fauziachmad1405', 'email': 'fauziachmad1405@gmail.com'},
            {'username': 'afnan.huwaiza@gmail.com', 'password': 'afnan.huwaiza', 'email': 'afnan.huwaiza@gmail.com'},
            {'username': 'anisahanun@student.telkomuniversity.ac.id', 'password': 'anisahanun', 'email': 'anisahanun@student.telkomuniversity.ac.id'},
            {'username': 'vanesarizka6@gmail.com', 'password': 'vanesarizka6', 'email': 'vanesarizka6@gmail.com'},
            {'username': 'zakisumanta@gmail.com', 'password': 'zakisumanta', 'email': 'zakisumanta@gmail.com'},
            {'username': 'mfarras.kmll@gmail.com', 'password': 'mfarras.kmll', 'email': 'mfarras.kmll@gmail.com'},
            {'username': 'alyadavina819@gmail.com', 'password': 'alyadavina819', 'email': 'alyadavina819@gmail.com'},
            {'username': 'isteponsmurf@gmail.com', 'password': 'isteponsmurf', 'email': 'isteponsmurf@gmail.com'},
            {'username': 'lukasrcky@gmail.com', 'password': 'lukasrcky', 'email': 'lukasrcky@gmail.com'},
            {'username': 'zikrihilmi15@gmail.com', 'password': 'zikrihilmi15', 'email': 'zikrihilmi15@gmail.com'},
            {'username': 'dprawira247@gmail.com', 'password': 'dprawira247', 'email': 'dprawira247@gmail.com'},
            {'username': 'aisyahnurraihandanyputri@gmail.com', 'password': 'aisyahnurraihandanyputri', 'email': 'aisyahnurraihandanyputri@gmail.com'},
            {'username': 'zakiyymj@gmail.com', 'password': 'zakiyymj', 'email': 'zakiyymj@gmail.com'},
            {'username': 'alghazalidimas011@gmail.com', 'password': 'alghazalidimas011', 'email': 'alghazalidimas011@gmail.com'},
            {'username': 'gyebran777@gmail.com', 'password': 'gyebran777', 'email': 'gyebran777@gmail.com'},
            {'username': 'ahmadfaizalthaf@gmail.com', 'password': 'ahmadfaizalthaf', 'email': 'ahmadfaizalthaf@gmail.com'},
            {'username': 'mzkaa1234@gmail.com', 'password': 'mzkaa1234', 'email': 'mzkaa1234@gmail.com'},
            {'username': 'faahdil010@gmail.com', 'password': 'faahdil010', 'email': 'faahdil010@gmail.com'},
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
