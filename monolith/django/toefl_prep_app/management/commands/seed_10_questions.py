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
