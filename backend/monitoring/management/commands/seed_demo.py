from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.models import Alert, PaperUsage, PrintJob, Printer


class Command(BaseCommand):
    help = 'Create local demo records for the PrintPulse dashboard.'

    def handle(self, *args, **options):
        if Printer.objects.exists():
            self.stdout.write(self.style.WARNING('Demo data already exists.'))
            return

        now = timezone.now()
        printer_rows = [
            ('Epson L5290', 'Finance Office', Printer.ONLINE, 78, 2847, 184),
            ('HP LaserJet Pro', 'Admin Office', Printer.ONLINE, 46, 1923, 142),
            ('Canon G4010', 'Registrar Office', Printer.ATTENTION, 12, 1174, 96),
        ]
        printer_objects = []
        for name, location, status, paper_level, pages, jobs in printer_rows:
            printer_objects.append(Printer.objects.create(
                name=name,
                location=location,
                status=status,
                paper_level=paper_level,
                total_pages=pages,
                total_jobs=jobs,
                last_seen=now - timedelta(minutes=2),
            ))

        job_rows = [
            ('Maria Santos', 0, 12, 'A4', PrintJob.COMPLETED, 0),
            ('James Lim', 1, 4, 'Short', PrintJob.COMPLETED, 7),
            ('Ana Reyes', 2, 25, 'Long', PrintJob.PRINTING, 11),
            ('Carlos Dela Cruz', 0, 8, 'A4', PrintJob.COMPLETED, 24),
        ]
        for user_name, printer_index, pages, paper_size, status, minutes_ago in job_rows:
            PrintJob.objects.create(
                user_name=user_name,
                printer=printer_objects[printer_index],
                pages=pages,
                paper_size=paper_size,
                status=status,
                created_at=now - timedelta(minutes=minutes_ago),
            )

        for paper_size, sheets in [('A4', 2427), ('Short', 1536), ('Long', 849)]:
            PaperUsage.objects.create(paper_size=paper_size, sheets=sheets, usage_date=timezone.localdate())

        Alert.objects.bulk_create([
            Alert(printer=printer_objects[2], alert_type=Alert.LOW_PAPER, detail='Canon G4010 • 12% remaining', severity='warning', created_at=now - timedelta(minutes=12)),
            Alert(printer=printer_objects[0], alert_type=Alert.OFFLINE, detail='Epson L3110 • Connection lost', severity='error', created_at=now - timedelta(hours=1)),
            Alert(printer=printer_objects[1], alert_type=Alert.PAPER_JAM, detail='HP LaserJet Pro • Tray 1', severity='warning', created_at=now - timedelta(hours=2)),
        ])
        self.stdout.write(self.style.SUCCESS('PrintPulse demo data created.'))
