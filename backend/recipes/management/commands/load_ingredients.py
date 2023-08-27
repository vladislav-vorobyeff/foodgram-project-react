import csv
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка данных из ingredients.csv'

    def add_arguments(self, parser):
        parser.add_argument('filename', default='ingredients.csv', nargs='?',
                            type=str)

    def handle(self, *args, **options):
        with open(
            'foodgram/data/ingredients.csv',
            encoding='utf8'
        ) as csv_file:
            data = csv.reader(csv_file)
            Ingredient.objects.bulk_create(
                (Ingredient(
                    name=row[0],
                    measurement_unit=row[1])
                    for row in data),
                batch_size=999
            )
