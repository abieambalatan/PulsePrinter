from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.models import Printer
from monitoring.services.spooler import discover_windows_printers


class Command(BaseCommand):
    help = 'Sync locally installed Windows printers into the PrintPulse database.'

    def handle(self, *args, **options):
        discovered = discover_windows_printers()
        if not discovered:
            self.stdout.write(self.style.WARNING('No Windows printers found or pywin32 is unavailable.'))
            return

        for row in discovered:
            Printer.objects.update_or_create(
                name=row['name'],
                defaults={
                    'status': row['status'],
                    'connection_type': 'Windows Spooler',
                    'last_seen': timezone.now(),
                },
            )
        self.stdout.write(self.style.SUCCESS(f'Synced {len(discovered)} printer(s).'))
