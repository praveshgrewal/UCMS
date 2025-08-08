from django.core.management.base import BaseCommand
from alumni.utils import import_alumni_from_excel

class Command(BaseCommand):
    help = 'Import alumni data from Excel file'
    
    def handle(self, *args, **options):
        self.stdout.write('Starting Excel import...')
        count = import_alumni_from_excel()
        self.stdout.write(
            self.style.SUCCESS(f'Successfully imported {count} alumni records')
        )