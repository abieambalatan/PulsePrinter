import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create or update the PrintPulse administrator account.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--email', default='')
        parser.add_argument('--password')

    def handle(self, *args, **options):
        username = options['username'].strip()
        password = options['password'] or getpass.getpass('Admin password: ')
        if not username or not password:
            raise CommandError('Username and password are required.')

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(username=username, defaults={'email': options['email']})
        user.email = options['email']
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        action = 'created' if created else 'updated'
        self.stdout.write(self.style.SUCCESS(f'Admin account {action}: {username}'))
