import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create the first administrator from deployment environment settings.'

    def handle(self, *args, **options):
        username = os.environ.get('PRINTPULSE_INITIAL_ADMIN_USERNAME', 'admin').strip()
        password = os.environ.get('PRINTPULSE_INITIAL_ADMIN_PASSWORD', '')
        if not username or not password:
            self.stdout.write(self.style.WARNING('Initial admin settings are not configured; skipping.'))
            return

        user_model = get_user_model()
        if user_model.objects.filter(is_staff=True).exists():
            self.stdout.write('An administrator already exists; leaving existing accounts unchanged.')
            return

        user = user_model.objects.filter(username=username).first()
        if user:
            raise CommandError('The configured initial admin username is already used by a non-admin account.')

        user_model.objects.create_superuser(username=username, password=password)
        self.stdout.write(self.style.SUCCESS(f'Created initial PrintPulse administrator: {username}'))
