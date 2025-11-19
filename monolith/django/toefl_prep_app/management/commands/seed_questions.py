# seed_questions.py

from django.core.management.base import BaseCommand
from toefl_prep_app.models import Question, Choice, CorrectAnswer

class Command(BaseCommand):
    help = 'Seed questions and choices data'

    def handle(self, *args, **kwargs):
        # Sample data for questions and choices
        questions_data = [
            {
                'question_text': 'Geothermal energy is a potentially inexhaustible energy resource … been tapped by humans for centuries but, until recent years, only on a small scale.',
                'choices': ['has it', 'has', 'that has', 'that it has'],
                'correct_choice_index': 2  # Index of correct choice in choices list
            },
            {
                'question_text': "The importance of the hand, and more generally of the body, in children’s acquisition of arithmetic …",
                'choices': ['can hardly be exaggerated', 'hardly exaggerated can be', 'can be exaggerate hardly', 'exaggerated can be hardly'],
                'correct_choice_index': 0  # Index of correct choice in choices list
            },
            {
                'question_text': '… is present in the body in greater amounts than any other mineral.',
                'choices': ['Calcium', 'There is calcium', 'Calcium, which', 'It is calcium'],
                'correct_choice_index': 0  # Index of correct choice in choices list
            },
            {
                'question_text': '… the evidence is inconclusive, it is thought that at least some seals have an echolocation system akin to that bats, porpoises, and shrews.',
                'choices': ['Rather', 'Despite', 'Although', 'Why'],
                'correct_choice_index': 2  # Index of correct choice in choices list
            },
            {
                'question_text': "The total mass of all asteroids in the solar system is much less … mass of Earth’s Moon.",
                'choices': ['than that is the', 'than the', 'the', 'is the'],
                'correct_choice_index': 1  # Index of correct choice in choices list
            },
            {
                'question_text': 'Like bacteria, protozoans … by splitting in two.',
                'choices': ['reproducing', 'reproduce', 'to reproduce', 'reproduction'],
                'correct_choice_index': 1  # Index of correct choice in choices list
            },
            {
                'question_text': '… main processes involved in virtually all manufacturing: extraction, assembly, and alteration.',
                'choices': ['There are three', 'Three', 'The three', 'Three of the'],
                'correct_choice_index': 0  # Index of correct choice in choices list
            },
            {
                'question_text': 'Most documentary film makers use neither actors … studio setting.',
                'choices': ['or else', 'but not', 'nor', 'and'],
                'correct_choice_index': 2  # Index of correct choice in choices list
            },
            {
                'question_text': 'Salamanders are sometime confused with lizards, but unlike lizards … no scales or claws.		',
                'choices': ['that they have', 'to have', 'they have', 'are having'],
                'correct_choice_index': 2  # Index of correct choice in choices list
            },
            {
                'question_text': 'The province of Alberta lies along three of the major North American flyways Used by birds … between their winter and summer homes',
                'choices': ['the migration', 'migrating', 'migrate', 'and migrate'],
                'correct_choice_index': 1  # Index of correct choice in choices list
            },
            {
                'question_text': 'Astronomers estimate … called the  Pleiades in the constellation Taurus is 415 light-years away from Earth.',
                'choices': ['that a loose cluster of stars', 'a loose cluster of stars is ', 'that is a loose cluster of stars', 'there is a loose cluster of stars'],
                'correct_choice_index': 0  # Index of correct choice in choices list
            },
            {
                'question_text': 'Pearl Sydenstricker Buck, … the Nobel Prize for Literature in 1938 is known for her novels about China.',
                'choices': ['won', 'winner of', 'to win', 'who the winner of'],
                'correct_choice_index': 1  # Index of correct choice in choices list
            },
            {
                'question_text': 'Stage producers Klaw and Erlanger were the first to eliminate arguments among leading performers … in order od appearance, instead of prominence.',
                'choices': ['of whom list the program', 'the program listing', 'for them the program listed', 'by listing them on the program'],
                'correct_choice_index': 3  # Index of correct choice in choices list
            },
            {
                'question_text': 'During the decades after the United States Civil War, a host of technical advances made possible … and uniformity of railroad service.',
                'choices': ['a new integration', 'for a new integration', 'that a new integration', 'and a new integration'],
                'correct_choice_index': 0  # Index of correct choice in choices list
            },
            {
                'question_text': 'Forests stabilize … and retain precipitation, thereby helping to prevent erosion and regulate the flow of streams.',
                'choices': ['to the soil', 'the soil', 'where the soil', 'the soil is'],
                'correct_choice_index': 1  # Index of correct choice in choices list
            },
            {
                'question_text': 'Modern societies are <u>such</u> complex that they could not <u>exist</u> <u>without</u> a well-developed <u>system</u> of law.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 0  # Index of correct choice in choices list
            },
            {
                'question_text': 'Altitude, climate, <u>temperature</u>, and the <u>length</u> of the growing season <u>both</u> determine where <u>plants</u> will grow',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 2  # Index of correct choice in choices list
            },
            {
                'question_text': 'The bathyscaphe, a free-moving vessel <u>designed</u> for underwater exploration, <u>consists</u> of a Flotation compartment <u>with a</u> observation capsule <u>attached underneath</u> it.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 2  # Index of correct choice in choices list
            },
            {
                'question_text': 'Water <u>constitutes</u> almost 96 percent of the <u>body weight</u> of a jelly fish, so if a jelly fish <u>were to</u> dry out in the sun, it would virtually <u>disappeared</u>.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 3  # Index of correct choice in choices list
            },
            {
                'question_text': "The most important <u>parameters</u> affecting a rocket’s maximum flight velocity is the relationship <u>between</u> the vehicle’s mass and the <u>amount</u> of propellant it <u>can carry</u>.",
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 0  # Index of correct choice in choices list
            },
            {
                'question_text': 'There <u>were once</u> only eight major lakes or reservoirs in Texas, but <u>today</u> there are over 180, <u>many</u> built <u>to storing</u> water against periodic droughts',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 3  # Index of correct choice in choices list
            },
            {
                'question_text': '<u>All</u> harmonized music that is not contrapuntal <u>depends from</u> the relationship of <u>chords</u>, which are <u>either</u> consonant or dissonant.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 1  # Index of correct choice in choices list
            },
            {
                'question_text': 'Expressionist drama often <u>shows</u> the <u>influence</u> of modern psychology <u>by reflecting</u> the <u>frustration inner</u> of the dramatist.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 3  # Index of correct choice in choices list
            },
            {
                'question_text': '<u>It is</u> the number , kind, and <u>arrange</u> of teeth that determine <u>whether</u> a mammal is classified as a carnivore not the food that the animal <u>actually eats</u>.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 1  # Index of correct choice in choices list
            },
            {
                'question_text': 'The sea otter is <u>well</u> adapted <u>at</u> <u>its</u> marine existence , with ears and nostrils that <u>can be</u> closed under water.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 1  # Index of correct choice in choices list
            },
            {
                'question_text': "Petroleum, which currently <u>makes up</u> about four-tenths of the world’s energy <u>production</u>, supplies more commercial energy than <u>any another</u> <u>source</u>.",
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 2  # Index of correct choice in choices list
            },
            {
                'question_text': 'Someone <u>may</u> refuse <u>to recognize</u> the seriousness of an emotionally <u>threatening</u> situation and <u>perceive as</u> less threatening.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 3  # Index of correct choice in choices list
            },
            {
                'question_text': '<u>Through</u> experiments with marine organisms, marine biologists <u>can increase</u> our knowledge of human <u>reproductive</u> and development as well as our <u>understanding</u> of the nervous system.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 2  # Index of correct choice in choices list
            },
            {
                'question_text': '<u>When swollen</u> by <u>melting</u> snow or heavy rain, some rivers <u>routinely</u> overflow <u>its</u> banks.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 3  # Index of correct choice in choices list
            },
            {
                'question_text': 'In 1884 Belva Lockwood, a lawyer <u>who</u> <u>had appeared</u> before the Supreme Court, became the <u>first</u> woman <u>was nominated</u> for President of the United States.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 3  # Index of correct choice in choices list
            },
            {
                'question_text': 'The <u>taller</u> of all animals, a <u>full-grown</u> giraffe <u>may be</u> eighteen feet or <u>more</u> high.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 0  # Index of correct choice in choices list
            },
            {
                'question_text': 'Physicists have known <u>since</u> the early nineteenth century <u>that</u> all matter is <u>made up</u> of <u>tiny extremely</u> particles called atoms.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 3  # Index of correct choice in choices list
            },
            {
                'question_text': 'Rain is <u>slight</u> acidic even in unpolluted air, <u>because</u> carbon dioxide in the atmosphere <u>and other</u> natural acidic-forming gases <u>dissolve</u> in the water.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 0  # Index of correct choice in choices list
            },
            {
                'question_text': 'In a stock company, a troupe of <u>actors</u> performs in a particular theatre, <u>presenting</u> plays from <u>its</u> repertory of <u>prepare</u> productions.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 3  # Index of correct choice in choices list
            },
            {
                'question_text': '<u>Established</u> in 1860, the Government Printing Office <u>prints and binds</u> documents for all <u>department</u> of the United States <u>government</u>.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 2  # Index of correct choice in choices list
            },
            {
                'question_text': 'Ethnology, usually considered <u>a branch</u> of cultural anthropology, is often <u>defined as</u> the <u>scientifically</u> study of the origin and functioning of humans and <u>their</u> culture.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 2  # Index of correct choice in choices list
            },
            {
                'question_text': 'The one-fluid theory <u>of electricity</u> was <u>proposing</u> by Benjamin Franklin, a <u>man</u> famous for <u>his</u> wide interests and great attainments.',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 1  # Index of correct choice in choices list
            },
            {
                'question_text': "Probably <u>not speech</u> of <u>so</u> few words <u>has</u> ever been <u>as celebrated as</u> Lincoln’s Gettysburg Address.",
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 0  # Index of correct choice in choices list
            },
            {
                'question_text': '<u>Generally</u>, Abstract Expressionist art is without recognizable images <u>and does</u> not <u>adhere the</u> Limits of conventional <u>form.</u>',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 2  # Index of correct choice in choices list
            },
            {
                'question_text': '<u>Although</u> <u>complete</u> paralysis is <u>rare with</u> neuritis, some degree of muscle <u>weakness common</u>',
                'choices': ['A', 'B', 'C', 'D'],
                'correct_choice_index': 3  # Index of correct choice in choices list
            },


            # Add more question data here
        ]

        for question_data in questions_data:
            question = Question.objects.create(question_text=question_data['question_text'])

            # Create choices for the question
            for choice_text in question_data['choices']:
                choice = Choice.objects.create(question=question, choice_text=choice_text)

            # Set the correct answer for the question
            correct_choice_index = question_data['correct_choice_index']
            correct_choice = Choice.objects.filter(question=question)[correct_choice_index]

            # Create CorrectAnswer instance and associate it with the question
            correct_answer = CorrectAnswer.objects.create(question=question, correct_choice=correct_choice)

        self.stdout.write(self.style.SUCCESS('Questions and choices seeded successfully.'))
