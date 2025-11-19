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
            {'username':'122230163@student.upnyk.ac.id', 'password': 'Toefl-1-Yacintha', 'email': '122230163@student.upnyk.ac.id'},
            {'username':'122230152@student.upnyk.ac.id', 'password': 'Toefl-2-Yohanna', 'email': '122230152@student.upnyk.ac.id'},
            {'username':'aliyahhikmah741@gmail.com', 'password': 'Toefl-3-Wahidah', 'email': 'aliyahhikmah741@gmail.com'},
            {'username':'terociauln@gmail.com', 'password': 'Toefl-4-Teroci', 'email': 'terociauln@gmail.com'},
            {'username':'122220114@student.upnyk.ac.id', 'password': 'Toefl-5-Hilmia', 'email': '122220114@student.upnyk.ac.id'},
            {'username':'diniherawati39@gmail.com', 'password': 'Toefl-6-DINI', 'email': 'diniherawati39@gmail.com'},
            {'username':'yasindiamond111@gmail.com', 'password': 'Toefl-7-Yasin', 'email': 'yasindiamond111@gmail.com'},
            {'username':'berlianojwala12@gmail.com', 'password': 'Toefl-8-Berlian', 'email': 'berlianojwala12@gmail.com'},
            {'username':'alfiqraffi04@gmail.com', 'password': 'Toefl-9-Alfiq', 'email': 'alfiqraffi04@gmail.com'},
            {'username':'raihanfirdausy261104@gmail.com', 'password': 'Toefl-10-Raihan', 'email': 'raihanfirdausy261104@gmail.com'},
            {'username':'naylaekaputrisalsabila086@gmail.com', 'password': 'Toefl-11-NAYLA', 'email': 'naylaekaputrisalsabila086@gmail.com'},
            {'username':'rifdaharyahiyya@gmail.com', 'password': 'Toefl-12-rifdah', 'email': 'rifdaharyahiyya@gmail.com'},
            {'username':'arieladitama35@gmail.com', 'password': 'Toefl-13-M', 'email': 'arieladitama35@gmail.com'},
            {'username':'nuranihandayani00@gmail.com', 'password': 'Toefl-14-Nurani', 'email': 'nuranihandayani00@gmail.com'},
            {'username':'dewidianp20@gmail.com', 'password': 'Toefl-15-Dewi', 'email': 'dewidianp20@gmail.com'},
            {'username':'r.hashif.r.r@gmail.com', 'password': 'Toefl-16-Raden', 'email': 'r.hashif.r.r@gmail.com'},
            {'username':'wulankhuriputri@gmail.com', 'password': 'Toefl-17-wulan', 'email': 'wulankhuriputri@gmail.com'},
            {'username':'marialarasati56@gmail.com', 'password': 'Toefl-18-Maria', 'email': 'marialarasati56@gmail.com'},
            {'username':'muchtarpanji06@gmail.com', 'password': 'Toefl-19-Muchtar', 'email': 'muchtarpanji06@gmail.com'},
            {'username':'zahra.pradani@gmail.com', 'password': 'Toefl-20-Azzahra', 'email': 'zahra.pradani@gmail.com'},
            {'username':'ameliahandinii@gmail.com', 'password': 'Toefl-21-Amelia', 'email': 'ameliahandinii@gmail.com'},
            {'username':'netta.cb28@gmail.com', 'password': 'Toefl-22-Garneta', 'email': 'netta.cb28@gmail.com'},
            {'username':'Cahyaningseptyani@gmail.com', 'password': 'Toefl-23-Cahyaning', 'email': 'Cahyaningseptyani@gmail.com'},
            {'username':'zanilla600@gmail.com', 'password': 'Toefl-24-Zanilla', 'email': 'zanilla600@gmail.com'},
            {'username':'enyasetiya@gmail.com', 'password': 'Toefl-25-Enya', 'email': 'enyasetiya@gmail.com'},
            {'username':'Divatama01@gmail.com', 'password': 'Toefl-26-Oktavia', 'email': 'Divatama01@gmail.com'},
            {'username':'nadanasyfa@gmail.com', 'password': 'Toefl-27-Nada', 'email': 'nadanasyfa@gmail.com'},
            {'username':'hidaya.dzikru@gmail.com', 'password': 'Toefl-28-Dzikru', 'email': 'hidaya.dzikru@gmail.com'},
            {'username':'maghfiradimas.mdr@gmail.com', 'password': 'Toefl-29-Maghfira', 'email': 'maghfiradimas.mdr@gmail.com'},
            {'username':'mhmdtaufikk12@gmail.com', 'password': 'Toefl-30-Muhamad', 'email': 'mhmdtaufikk12@gmail.com'},
            {'username':'adelianrakhili@gmail.com', 'password': 'Toefl-31-Adelia', 'email': 'adelianrakhili@gmail.com'},
            {'username':'luckysetiawansalim@gmail.com', 'password': 'Toefl-32-Lucky', 'email': 'luckysetiawansalim@gmail.com'},
            {'username':'nabilaintania3@gmail.com', 'password': 'Toefl-33-Nabila', 'email': 'nabilaintania3@gmail.com'},
            {'username':'jihandinda5@gmail.com', 'password': 'Toefl-34-Wildan', 'email': 'jihandinda5@gmail.com'},
            {'username':'sarahsianturi05@gmail.com', 'password': 'Toefl-35-Sarah', 'email': 'sarahsianturi05@gmail.com'},
            {'username':'122220213@student.upnyk.ac.id', 'password': 'Toefl-36-Muhammad', 'email': '122220213@student.upnyk.ac.id'},
            {'username':'annisazni8@gmail.com', 'password': 'Toefl-37-Annisa', 'email': 'annisazni8@gmail.com'},
            {'username':'amandakhairunnisap@gmail.com', 'password': 'Toefl-38-Putri', 'email': 'amandakhairunnisap@gmail.com'},
            {'username':'122210044@student.upnyk.ac.id', 'password': 'Toefl-39-Jonathan', 'email': '122210044@student.upnyk.ac.id'},
            {'username':'122230144@student.upnyk.ac.id', 'password': 'Toefl-40-ALVANDY', 'email': '122230144@student.upnyk.ac.id'},
            {'username':'mputcamelia04@gmail.com', 'password': 'Toefl-41-putri', 'email': 'mputcamelia04@gmail.com'},
            {'username':'syifanurauliarosyada@gmail.com', 'password': 'Toefl-42-Syifa', 'email': 'syifanurauliarosyada@gmail.com'},
            {'username':'raflibayu06@gmail.com', 'password': 'Toefl-43-Rafli', 'email': 'raflibayu06@gmail.com'},
            {'username':'akbarhebat.2017@gmail.com', 'password': 'Toefl-44-Derwin', 'email': 'akbarhebat.2017@gmail.com'},
            {'username':'lupapasswoord0126@gmail.com', 'password': 'Toefl-45-Helmi', 'email': 'lupapasswoord0126@gmail.com'},
            {'username':'azkarizaldi21@gmail.com', 'password': 'Toefl-46-Harish', 'email': 'azkarizaldi21@gmail.com'},
            {'username':'ridhoraihan98@gmail.com', 'password': 'Toefl-47-Ridho', 'email': 'ridhoraihan98@gmail.com'},
            {'username':'bengawanpangayoman2235@gmail.com', 'password': 'Toefl-48-Bengawan', 'email': 'bengawanpangayoman2235@gmail.com'},
            {'username':'nasywaroesvianaputrii@gmail.com', 'password': 'Toefl-49-Nasywa', 'email': 'nasywaroesvianaputrii@gmail.com'},
            {'username':'nurpt.utami@gmail.com', 'password': 'Toefl-50-Nur', 'email': 'nurpt.utami@gmail.com'},
            {'username':'eleazarhendri@gmail.com', 'password': 'Toefl-51-Eleazar', 'email': 'eleazarhendri@gmail.com'},
            {'username':'zulfasyarifah12@gmail.com', 'password': 'Toefl-52-Zulfa', 'email': 'zulfasyarifah12@gmail.com'},
            {'username':'yuliarahayu473@gmail.com', 'password': 'Toefl-53-yulia', 'email': 'yuliarahayu473@gmail.com'},
            {'username':'shabrinahp07@gmail.com', 'password': 'Toefl-54-shabrina', 'email': 'shabrinahp07@gmail.com'},
            {'username':'zakiyyulkauni@gmail.com', 'password': 'Toefl-55-Muhammad', 'email': 'zakiyyulkauni@gmail.com'},
            {'username':'universakyola@gmail.com', 'password': 'Toefl-56-Kayla', 'email': 'universakyola@gmail.com'},
            {'username':'nabilaauliafauzan18@gmail.com', 'password': 'Toefl-57-Nabila', 'email': 'nabilaauliafauzan18@gmail.com'},
            {'username':'Zikriwibi@gmail.com', 'password': 'Toefl-58-Zikri', 'email': 'Zikriwibi@gmail.com'},
            {'username':'muazarahfatihah20@gmail.com', 'password': 'Toefl-59-Fatihah', 'email': 'muazarahfatihah20@gmail.com'},
            {'username':'122210129@student.upnyk.ac.id ', 'password': 'Toefl-60-Priscilla', 'email': '122210129@student.upnyk.ac.id '},
            {'username':'Cleopatratasya45@gmail.com', 'password': 'Toefl-61-Cleopatra', 'email': 'Cleopatratasya45@gmail.com'},
            {'username':'marizaa.murti@gmail.com', 'password': 'Toefl-62-Mariza', 'email': 'marizaa.murti@gmail.com'},

            

            # Add more user data as needed
        ]
        for data in users_data:
            user = User.objects.create_user(**data)
            UserProfile.objects.create(user=user)
        self.stdout.write(self.style.SUCCESS('Users seeded successfully.'))
