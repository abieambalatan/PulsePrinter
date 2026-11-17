from django.db import models
from django.db.models import Q


class Printer(models.Model):
    ONLINE = 'Online'
    OFFLINE = 'Offline'
    ATTENTION = 'Attention'
    STATUS_CHOICES = [(ONLINE, 'Online'), (OFFLINE, 'Offline'), (ATTENTION, 'Attention')]

    name = models.CharField(max_length=120)
    location = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=OFFLINE)
    paper_level = models.PositiveSmallIntegerField(default=0)
    total_pages = models.PositiveIntegerField(default=0)
    total_jobs = models.PositiveIntegerField(default=0)
    connection_type = models.CharField(max_length=30, default='Windows Spooler')
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PrintJob(models.Model):
    COMPLETED = 'Completed'
    PRINTING = 'Printing'
    FAILED = 'Failed'
    STATUS_CHOICES = [(COMPLETED, 'Completed'), (PRINTING, 'Printing'), (FAILED, 'Failed')]
    PAPER_CHOICES = [('A4', 'A4'), ('Short', 'Short / Letter'), ('Long', 'Long / Legal'), ('Unknown', 'Unknown')]

    user_name = models.CharField(max_length=120)
    printer = models.ForeignKey(Printer, on_delete=models.CASCADE, related_name='print_jobs')
    pages = models.PositiveIntegerField(default=1)
    paper_size = models.CharField(max_length=20, choices=PAPER_CHOICES, default='A4')
    document_name = models.CharField(max_length=255, blank=True)
    source_machine = models.CharField(max_length=120, blank=True)
    source_event_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=COMPLETED)
    created_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['source_machine', 'source_event_id'], condition=~Q(source_event_id=''), name='unique_print_event_source'),
        ]


class PaperUsage(models.Model):
    paper_size = models.CharField(max_length=20, choices=PrintJob.PAPER_CHOICES)
    sheets = models.PositiveIntegerField(default=0)
    usage_date = models.DateField()

    class Meta:
        ordering = ['-usage_date', 'paper_size']


class Alert(models.Model):
    LOW_PAPER = 'Low paper level'
    OFFLINE = 'Printer offline'
    PAPER_JAM = 'Paper jam detected'
    PRINT_ERROR = 'Printing error'
    TYPE_CHOICES = [(LOW_PAPER, LOW_PAPER), (OFFLINE, OFFLINE), (PAPER_JAM, PAPER_JAM), (PRINT_ERROR, PRINT_ERROR)]

    printer = models.ForeignKey(Printer, null=True, blank=True, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=40, choices=TYPE_CHOICES)
    detail = models.CharField(max_length=200)
    severity = models.CharField(max_length=20, default='warning')
    is_resolved = models.BooleanField(default=False)
    source_machine = models.CharField(max_length=120, blank=True)
    source_event_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['source_machine', 'source_event_id'], condition=~Q(source_event_id=''), name='unique_alert_event_source'),
        ]
