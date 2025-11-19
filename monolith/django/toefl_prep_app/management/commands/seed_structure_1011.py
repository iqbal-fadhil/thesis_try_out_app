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
