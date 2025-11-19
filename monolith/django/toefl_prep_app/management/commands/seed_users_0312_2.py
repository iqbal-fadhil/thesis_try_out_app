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
            {'username': 'rlianisyah@gmail.com', 'password': 'rlianisyah', 'email': 'rlianisyah@gmail.com'},
            {'username': 'riefaniptr@gmail.com', 'password': 'riefaniptr', 'email': 'riefaniptr@gmail.com'},
            {'username': 'raihantridar@gmail.com', 'password': 'raihantridar', 'email': 'raihantridar@gmail.com'},
            {'username': 'mhmdfazrill@student.telkomuniversity.ac.id', 'password': 'mhmdfazrill', 'email': 'mhmdfazrill@student.telkomuniversity.ac.id'},
            {'username': 'biannso4@gmail.com', 'password': 'biannso4', 'email': 'biannso4@gmail.com'},
            {'username': 'deazard@student.telkomuniversity.ac.id', 'password': 'deazard', 'email': 'deazard@student.telkomuniversity.ac.id'},
            {'username': 'albiyandc@student.telkomuniversity.ac.id', 'password': 'albiyandc', 'email': 'albiyandc@student.telkomuniversity.ac.id'},
            {'username': 'challysoloz@gmail.com', 'password': 'challysoloz', 'email': 'challysoloz@gmail.com'},
            {'username': 'vikifirmansyah24@gmail.com', 'password': 'vikifirmansyah24', 'email': 'vikifirmansyah24@gmail.com'},
            {'username': 'ketrin060405@gmail.com', 'password': 'ketrin060405', 'email': 'ketrin060405@gmail.com'},
            {'username': 'farrasikhsanulr@student.telkomuniversity.ac.id', 'password': 'farrasikhsanulr', 'email': 'farrasikhsanulr@student.telkomuniversity.ac.id'},
            {'username': 'syarahalfarisyah@student.telkomuniversity.ac.id', 'password': 'syarahalfarisyah', 'email': 'syarahalfarisyah@student.telkomuniversity.ac.id'},
            {'username': 'nadhifaqila@student.telkomuniversity.ac.id', 'password': 'nadhifaqila', 'email': 'nadhifaqila@student.telkomuniversity.ac.id'},
            {'username': 'andrariezarizqip@student.telkomuniversity.ac.id', 'password': 'andrariezarizqip', 'email': 'andrariezarizqip@student.telkomuniversity.ac.id'},
            {'username': 'azkaalmulki@student.telkomuniversity.ac.id', 'password': 'azkaalmulki', 'email': 'azkaalmulki@student.telkomuniversity.ac.id'},
            {'username': 'neilson76t@gmail.com', 'password': 'neilson76t', 'email': 'neilson76t@gmail.com'},
            {'username': 'nawfaldo.fazli@gmail.com', 'password': 'nawfaldo.fazli', 'email': 'nawfaldo.fazli@gmail.com'},
            {'username': 'puanazkia@gmail.comnnnnnn', 'password': 'puanazkia', 'email': 'puanazkia@gmail.comnnnnnn'},
            {'username': 'habibi.budiman321@gmail.com', 'password': 'habibi.budiman321', 'email': 'habibi.budiman321@gmail.com'},
            {'username': 'ryanibnu2017@gmail.com', 'password': 'ryanibnu2017', 'email': 'ryanibnu2017@gmail.com'},
            {'username': 'reyhanthariq27@gmail.com', 'password': 'reyhanthariq27', 'email': 'reyhanthariq27@gmail.com'},
            {'username': 'yasifaputriprasetio@student.telkomuniversity.ac.id', 'password': 'yasifaputriprasetio', 'email': 'yasifaputriprasetio@student.telkomuniversity.ac.id'},
            {'username': 'arjunadpk6618@gmail.com', 'password': 'arjunadpk6618', 'email': 'arjunadpk6618@gmail.com'},
            {'username': 'rayhanfirdaus2018@gmail.com', 'password': 'rayhanfirdaus2018', 'email': 'rayhanfirdaus2018@gmail.com'},
            {'username': 'arjunarayihan@student.telkomuniversity.ac.id', 'password': 'arjunarayihan', 'email': 'arjunarayihan@student.telkomuniversity.ac.id'},
            {'username': 'sanishere@student.telkomuniversity.ac.id', 'password': 'sanishere', 'email': 'sanishere@student.telkomuniversity.ac.id'},
            {'username': 'aldomuskitta1@gmail.com', 'password': 'aldomuskitta1', 'email': 'aldomuskitta1@gmail.com'},
            {'username': 'adnanrizprat@student.telkomuniversity.ac.id', 'password': 'adnanrizprat', 'email': 'adnanrizprat@student.telkomuniversity.ac.id'},
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
