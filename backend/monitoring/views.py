from collections import defaultdict
from datetime import timedelta
from html import escape
from io import BytesIO
import hmac
import json
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, F, Sum
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Alert, PaperUsage, PrintJob, Printer


AVATAR_COLORS = ['coral', 'blue', 'violet', 'green']


def _user_data(user):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'name': user.get_full_name() or user.username,
        'is_staff': user.is_staff,
    }


def api_login_required(view_func):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({'detail': 'Admin authentication required.'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapped


def _printer_data(printer):
    return {
        'id': printer.id,
        'name': printer.name,
        'location': printer.location,
        'status': printer.status,
        'level': printer.paper_level,
        'jobs': printer.total_jobs,
        'pages': f'{printer.total_pages:,}',
        'paper_jams': printer.alerts.filter(alert_type=Alert.PAPER_JAM).count(),
        'connection_type': printer.connection_type,
        'last_seen': printer.last_seen.isoformat() if printer.last_seen else None,
    }


def _job_data(job, index=0):
    initials = ''.join(part[0] for part in job.user_name.split()[:2]).upper()
    return {
        'id': job.id,
        'user': job.user_name,
        'initials': initials,
        'color': AVATAR_COLORS[index % len(AVATAR_COLORS)],
        'printer': job.printer.name,
        'pages': job.pages,
        'paper': job.paper_size,
        'status': job.status,
        'time': timezone.localtime(job.created_at).strftime('%I:%M %p').lstrip('0'),
        'created_at': job.created_at.isoformat(),
    }


def _alert_data(alert):
    tone = 'red' if alert.alert_type == Alert.OFFLINE else 'orange' if alert.alert_type == Alert.LOW_PAPER else 'yellow'
    icon = 'printer' if alert.alert_type == Alert.OFFLINE else 'warning'
    age = timezone.localtime() - timezone.localtime(alert.created_at)
    minutes = max(1, int(age.total_seconds() // 60))
    time_label = f'{minutes} min ago' if minutes < 60 else f'{minutes // 60} hr ago'
    return {
        'id': alert.id,
        'title': alert.alert_type,
        'detail': alert.detail,
        'tone': tone,
        'icon': icon,
        'time': time_label,
        'is_resolved': alert.is_resolved,
    }


@require_GET
def health(request):
    return JsonResponse({'status': 'ok', 'service': 'printpulse-api'})


@require_GET
def frontend_app(request, path=''):
    frontend_dir = Path(os.environ.get(
        'PRINTPULSE_FRONTEND_DIR', Path(__file__).resolve().parents[2] / 'frontend-dist'
    ))
    index_file = frontend_dir / 'index.html'
    if not index_file.is_file():
        return JsonResponse({'detail': 'Frontend build is not installed.'}, status=404)
    return HttpResponse(index_file.read_text(encoding='utf-8'), content_type='text/html; charset=utf-8')


@require_GET
def csrf_token(request):
    return JsonResponse({'csrfToken': get_token(request)})


@require_POST
def auth_login(request):
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid request body.'}, status=400)

    user = authenticate(request, username=payload.get('username', '').strip(), password=payload.get('password', ''))
    if not user or not user.is_staff:
        return JsonResponse({'detail': 'Invalid admin credentials.'}, status=401)
    login(request, user)
    return JsonResponse({'user': _user_data(user)})


@require_POST
def auth_logout(request):
    logout(request)
    return JsonResponse({'status': 'ok'})


@require_GET
def auth_me(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'authenticated': False})
    return JsonResponse({'authenticated': True, 'user': _user_data(request.user)})


@require_POST
@api_login_required
def auth_profile_update(request):
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid request body.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'detail': 'Profile details must be an object.'}, status=400)

    user = request.user
    username = str(payload.get('username', '')).strip()
    email = str(payload.get('email', '')).strip()
    first_name = str(payload.get('first_name', '')).strip()
    last_name = str(payload.get('last_name', '')).strip()
    if not username:
        return JsonResponse({'detail': 'Username is required.'}, status=400)
    if len(username) > user._meta.get_field('username').max_length:
        return JsonResponse({'detail': 'Username is too long.'}, status=400)
    if user.__class__.objects.filter(username=username).exclude(pk=user.pk).exists():
        return JsonResponse({'detail': 'That username is already in use.'}, status=409)
    try:
        user._meta.get_field('username').run_validators(username)
        user._meta.get_field('email').run_validators(email)
    except ValidationError as error:
        return JsonResponse({'detail': error.messages[0]}, status=400)
    if len(first_name) > 150 or len(last_name) > 150:
        return JsonResponse({'detail': 'First and last names must be 150 characters or fewer.'}, status=400)

    user.username = username
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    user.save(update_fields=['username', 'email', 'first_name', 'last_name'])
    return JsonResponse({'user': _user_data(user)})


@require_GET
@api_login_required
def dashboard(request):
    completed_jobs = PrintJob.objects.filter(status=PrintJob.COMPLETED)
    total_pages = Printer.objects.aggregate(total=Sum('total_pages'))['total'] or 0
    total_sheets = PaperUsage.objects.aggregate(total=Sum('sheets'))['total'] or 0
    active_printers = Printer.objects.filter(status=Printer.ONLINE).count()
    unresolved_alerts = Alert.objects.filter(is_resolved=False)
    paper_rows = PaperUsage.objects.values('paper_size').annotate(sheets=Sum('sheets')).order_by('paper_size')
    paper_usage_data = [{'label': row['paper_size'], 'value': row['sheets']} for row in paper_rows]

    activity = defaultdict(int)
    today = timezone.localdate()
    for job in PrintJob.objects.filter(created_at__date__gte=today - timedelta(days=6), status=PrintJob.COMPLETED):
        activity[timezone.localtime(job.created_at).strftime('%a')] += job.pages

    return JsonResponse({
        'summary': {
            'total_pages': total_pages,
            'paper_consumed': total_sheets,
            'active_printers': active_printers,
            'total_printers': Printer.objects.count(),
            'detected_errors': unresolved_alerts.count(),
        },
        'activity': [{'day': day, 'pages': activity[day]} for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']],
        'paper_usage': paper_usage_data,
        'printers': [_printer_data(printer) for printer in Printer.objects.all()],
        'recent_jobs': [_job_data(job, index) for index, job in enumerate(PrintJob.objects.select_related('printer')[:10])],
        'alerts': [_alert_data(alert) for alert in unresolved_alerts[:10]],
    })


@require_http_methods(['GET', 'POST'])
@api_login_required
def printers(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'detail': 'Invalid request body.'}, status=400)

        name = payload.get('name', '').strip()
        if not name:
            return JsonResponse({'detail': 'Printer name is required.'}, status=400)
        if Printer.objects.filter(name__iexact=name).exists():
            return JsonResponse({'detail': 'A printer with this name already exists.'}, status=409)
        status = payload.get('status', Printer.OFFLINE)
        allowed_statuses = {choice[0] for choice in Printer.STATUS_CHOICES}
        if status not in allowed_statuses:
            return JsonResponse({'detail': 'Choose Online, Offline, or Attention for printer status.'}, status=400)
        try:
            paper_level = int(payload.get('paper_level', 0))
        except (TypeError, ValueError):
            return JsonResponse({'detail': 'Paper level must be a number from 0 to 100.'}, status=400)
        if not 0 <= paper_level <= 100:
            return JsonResponse({'detail': 'Paper level must be between 0 and 100.'}, status=400)

        printer = Printer.objects.create(
            name=name,
            location=payload.get('location', '').strip(),
            status=status,
            paper_level=paper_level,
            connection_type=payload.get('connection_type', 'Manual').strip() or 'Manual',
            last_seen=timezone.now() if status == Printer.ONLINE else None,
        )
        return JsonResponse({'printer': _printer_data(printer)}, status=201)

    return JsonResponse({'results': [_printer_data(printer) for printer in Printer.objects.all()]})


@require_POST
@api_login_required
def sync_printers(request):
    # Render cannot enumerate Windows printers installed on an office PC. The
    # local agent reports them to agent_sync_printers; this endpoint reports
    # which spooler printers have checked in recently.
    cutoff = timezone.now() - timedelta(minutes=3)
    recently_reported = Printer.objects.filter(
        connection_type='Windows Spooler', last_seen__gte=cutoff,
    ).order_by('name')
    return JsonResponse({
        'synced': recently_reported.count(),
        'printers': [_printer_data(printer) for printer in recently_reported],
    })


@csrf_exempt
@require_POST
def agent_sync_printers(request):
    """Receive installed printer inventory from a locally running Windows agent."""
    expected_token = settings.PRINTPULSE_AGENT_TOKEN
    if not expected_token:
        return JsonResponse({'detail': 'PrintPulse agent ingestion is not configured.'}, status=503)
    authorization = request.headers.get('Authorization', '')
    if not hmac.compare_digest(authorization, f'Bearer {expected_token}'):
        return JsonResponse({'detail': 'Agent authentication failed.'}, status=401)
    if len(request.body) > 65_536:
        return JsonResponse({'detail': 'Request body is too large.'}, status=413)
    try:
        payload = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'detail': 'Invalid JSON request body.'}, status=400)
    if not isinstance(payload, dict) or not isinstance(payload.get('printers'), list):
        return JsonResponse({'detail': 'A printers array is required.'}, status=400)
    source_machine = str(payload.get('source_machine', '')).strip()
    if not source_machine or len(source_machine) > 120:
        return JsonResponse({'detail': 'A valid source computer name is required.'}, status=400)

    received_at = timezone.now()
    synced = 0
    for row in payload['printers'][:200]:
        if not isinstance(row, dict):
            continue
        name = str(row.get('name', '')).strip()
        if not name or len(name) > 120:
            continue
        location = str(row.get('location', '')).strip()[:120]
        status = str(row.get('status', Printer.ONLINE)).strip()
        if status not in {choice[0] for choice in Printer.STATUS_CHOICES}:
            status = Printer.ONLINE
        defaults = {
            'status': status,
            'connection_type': 'Windows Spooler',
            'last_seen': received_at,
        }
        if location:
            defaults['location'] = location
        Printer.objects.update_or_create(name=name, defaults=defaults)
        synced += 1
    return JsonResponse({'synced': synced})


@require_GET
@api_login_required
def print_jobs(request):
    query = request.GET.get('q', '').strip()
    jobs = PrintJob.objects.select_related('printer')
    if query:
        jobs = jobs.filter(user_name__icontains=query) | jobs.filter(printer__name__icontains=query)
    return JsonResponse({'results': [_job_data(job, index) for index, job in enumerate(jobs[:100])]})


@csrf_exempt
@require_POST
def ingest_print_job(request):
    """Accept completed Windows spooler jobs from the authenticated office agent."""
    expected_token = settings.PRINTPULSE_AGENT_TOKEN
    if not expected_token:
        return JsonResponse({'detail': 'PrintPulse agent ingestion is not configured.'}, status=503)

    authorization = request.headers.get('Authorization', '')
    if not hmac.compare_digest(authorization, f'Bearer {expected_token}'):
        return JsonResponse({'detail': 'Agent authentication failed.'}, status=401)

    if len(request.body) > 16_384:
        return JsonResponse({'detail': 'Request body is too large.'}, status=413)
    try:
        payload = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'detail': 'Invalid JSON request body.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'detail': 'Request body must be a JSON object.'}, status=400)

    printer_name = str(payload.get('printer_name', '')).strip()
    user_name = str(payload.get('user_name', '')).strip()
    source_machine = str(payload.get('source_machine', '')).strip()
    source_event_id = str(payload.get('source_event_id', '')).strip()
    if not printer_name or len(printer_name) > 120:
        return JsonResponse({'detail': 'A printer name up to 120 characters is required.'}, status=400)
    if len(user_name) > 120 or not source_machine or len(source_machine) > 120:
        return JsonResponse({'detail': 'User or source computer name is invalid.'}, status=400)
    if not source_event_id or len(source_event_id) > 100:
        return JsonResponse({'detail': 'A Windows event record ID is required.'}, status=400)
    try:
        pages = int(payload.get('pages', 0))
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'Page count must be a whole number.'}, status=400)
    if pages < 0 or pages > 10_000_000:
        return JsonResponse({'detail': 'Page count is outside the accepted range.'}, status=400)

    paper_size = str(payload.get('paper_size', 'Unknown')).strip()
    allowed_paper_sizes = {choice[0] for choice in PrintJob.PAPER_CHOICES}
    if paper_size not in allowed_paper_sizes:
        paper_size = 'Unknown'

    printed_at = parse_datetime(str(payload.get('created_at', '')).strip())
    if printed_at is None:
        printed_at = timezone.now()
    elif timezone.is_naive(printed_at):
        printed_at = timezone.make_aware(printed_at, timezone.get_current_timezone())

    received_at = timezone.now()
    with transaction.atomic():
        printer = Printer.objects.filter(name__iexact=printer_name).first()
        if printer is None:
            printer = Printer.objects.create(
                name=printer_name,
                status=Printer.ONLINE,
                connection_type='Windows Spooler',
                last_seen=received_at,
            )

        _, created = PrintJob.objects.get_or_create(
            source_machine=source_machine,
            source_event_id=source_event_id,
            defaults={
                'user_name': user_name or 'Unknown user',
                'printer': printer,
                'pages': pages,
                'paper_size': paper_size,
                'status': PrintJob.COMPLETED,
                'created_at': printed_at,
            },
        )
        if created:
            Printer.objects.filter(pk=printer.pk).update(
                total_jobs=F('total_jobs') + 1,
                total_pages=F('total_pages') + pages,
                status=Printer.ONLINE,
                last_seen=received_at,
            )
            if paper_size != 'Unknown':
                usage_date = timezone.localdate(printed_at)
                usage, usage_created = PaperUsage.objects.get_or_create(
                    paper_size=paper_size,
                    usage_date=usage_date,
                    defaults={'sheets': pages},
                )
                if not usage_created:
                    PaperUsage.objects.filter(pk=usage.pk).update(sheets=F('sheets') + pages)

    return JsonResponse({'status': 'recorded' if created else 'duplicate'})


@require_GET
@api_login_required
def paper_usage(request):
    rows = PaperUsage.objects.values('paper_size').annotate(sheets=Sum('sheets')).order_by('paper_size')
    return JsonResponse({'results': [{'paper_size': row['paper_size'], 'sheets': row['sheets']} for row in rows]})


@require_GET
@api_login_required
def alerts(request):
    return JsonResponse({'results': [_alert_data(alert) for alert in Alert.objects.filter(is_resolved=False)[:100]]})


@require_GET
@api_login_required
def report_summary(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    completed = PrintJob.objects.filter(status=PrintJob.COMPLETED)
    return JsonResponse({
        'daily_pages': completed.filter(created_at__date=today).aggregate(total=Sum('pages'))['total'] or 0,
        'monthly_pages': completed.filter(created_at__date__gte=month_start).aggregate(total=Sum('pages'))['total'] or 0,
        'total_pages': Printer.objects.aggregate(total=Sum('total_pages'))['total'] or 0,
        'total_sheets': PaperUsage.objects.aggregate(total=Sum('sheets'))['total'] or 0,
        'printer_errors': Alert.objects.count(),
    })


@require_GET
@api_login_required
def export_report(request):
    generated_at = timezone.localtime()
    start_value = request.GET.get('start_date', '').strip()
    end_value = request.GET.get('end_date', '').strip()
    start_date = parse_date(start_value) if start_value else None
    end_date = parse_date(end_value) if end_value else None
    if start_value and start_date is None:
        return JsonResponse({'detail': 'Start date must use YYYY-MM-DD format.'}, status=400)
    if end_value and end_date is None:
        return JsonResponse({'detail': 'End date must use YYYY-MM-DD format.'}, status=400)
    if start_date and end_date and start_date > end_date:
        return JsonResponse({'detail': 'Start date must be on or before end date.'}, status=400)

    paper_usage = PaperUsage.objects.all()
    job_history = PrintJob.objects.select_related('printer').all()
    completed_jobs = PrintJob.objects.filter(status=PrintJob.COMPLETED)
    error_history = Alert.objects.select_related('printer').all()
    if start_date:
        paper_usage = paper_usage.filter(usage_date__gte=start_date)
        job_history = job_history.filter(created_at__date__gte=start_date)
        completed_jobs = completed_jobs.filter(created_at__date__gte=start_date)
        error_history = error_history.filter(created_at__date__gte=start_date)
    if end_date:
        paper_usage = paper_usage.filter(usage_date__lte=end_date)
        job_history = job_history.filter(created_at__date__lte=end_date)
        completed_jobs = completed_jobs.filter(created_at__date__lte=end_date)
        error_history = error_history.filter(created_at__date__lte=end_date)

    paper_rows = list(paper_usage.values('paper_size').annotate(sheets=Sum('sheets')).order_by('paper_size'))
    total_sheets = sum(row['sheets'] or 0 for row in paper_rows)
    if start_date or end_date:
        total_pages = completed_jobs.aggregate(total=Sum('pages'))['total'] or 0
    else:
        total_pages = Printer.objects.aggregate(total=Sum('total_pages'))['total'] or 0
    total_printers = Printer.objects.count()
    total_errors = error_history.count()

    buffer = BytesIO()
    page_width, _ = landscape(A4)
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=20 * mm,
        bottomMargin=17 * mm,
        title='PrintPulse Printer Monitoring Report',
        author='PrintPulse Administrator',
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=21, leading=25, textColor=colors.HexColor('#17213d'), alignment=TA_CENTER, spaceAfter=4))
    styles.add(ParagraphStyle(name='ReportSubtitle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#778198'), alignment=TA_CENTER, spaceAfter=16))
    styles.add(ParagraphStyle(name='SectionHeading', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#27365d'), spaceBefore=12, spaceAfter=7, keepWithNext=True))
    styles.add(ParagraphStyle(name='CellText', parent=styles['BodyText'], fontSize=7.5, leading=9, textColor=colors.HexColor('#36415b')))
    styles.add(ParagraphStyle(name='SmallCell', parent=styles['BodyText'], fontSize=7, leading=8.5, textColor=colors.HexColor('#36415b')))
    styles.add(ParagraphStyle(name='TableHeader', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=colors.white))
    content_width = page_width - 32 * mm

    def safe_cell(value, style='CellText'):
        return Paragraph(escape(str(value if value is not None else '')), styles[style])

    def make_table(rows, widths, repeat_rows=1):
        table = LongTable(rows, colWidths=widths, repeatRows=repeat_rows, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#26365d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f6fa')]),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#dce2ec')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        return table

    story = [
        Paragraph('PRINTPULSE', styles['ReportTitle']),
        Paragraph('PRINTER MONITORING &amp; PAPER USAGE REPORT', styles['ReportSubtitle']),
        Paragraph(f'Generated {generated_at.strftime("%B %d, %Y at %I:%M %p")} · Prepared by administrator', styles['Normal']),
        Spacer(1, 10),
    ]
    if start_date or end_date:
        period_start = start_date.isoformat() if start_date else 'Beginning of recorded history'
        period_end = end_date.isoformat() if end_date else 'Present'
        story.extend([Paragraph(f'Reporting period: {escape(period_start)} to {escape(period_end)}', styles['Normal']), Spacer(1, 8)])
    summary = [
        ['TOTAL PAGES PRINTED', 'PAPER SHEETS USED', 'REGISTERED PRINTERS', 'RECORDED ERRORS'],
        [f'{total_pages:,}', f'{total_sheets:,}', f'{total_printers:,}', f'{total_errors:,}'],
    ]
    summary_table = Table(summary, colWidths=[content_width / 4] * 4)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef1ff')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#65708a')),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#26365d')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('FONTSIZE', (0, 1), (-1, 1), 16),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dce2ec')),
        ('INNERGRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#dce2ec')),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
    ]))
    story.extend([summary_table, Paragraph('Paper usage by size', styles['SectionHeading'])])
    paper_table_rows = [[safe_cell('Paper size', 'TableHeader'), safe_cell('Sheets used', 'TableHeader'), safe_cell('Share', 'TableHeader')]]
    for row in paper_rows:
        share = (row['sheets'] or 0) / total_sheets * 100 if total_sheets else 0
        paper_table_rows.append([safe_cell(row['paper_size']), safe_cell(f"{row['sheets']:,}"), safe_cell(f'{share:.1f}%')])
    if not paper_rows:
        paper_table_rows.append([safe_cell('No paper usage recorded'), safe_cell('0'), safe_cell('0.0%')])
    story.append(make_table(paper_table_rows, [content_width * .58, content_width * .21, content_width * .21]))

    story.append(Paragraph('Completed pages by printer and paper size', styles['SectionHeading']))
    usage_by_printer = defaultdict(lambda: {'total': 0, 'A4': 0, 'Short': 0, 'Long': 0, 'jobs': 0})
    for row in completed_jobs.values('printer_id', 'paper_size').annotate(pages=Sum('pages'), jobs=Count('id')):
        usage_by_printer[row['printer_id']]['total'] += row['pages'] or 0
        usage_by_printer[row['printer_id']][row['paper_size']] += row['pages'] or 0
        usage_by_printer[row['printer_id']]['jobs'] += row['jobs']

    printer_rows = [[safe_cell(label, 'TableHeader') for label in ['Printer', 'Total pages', 'A4 pages', 'Short / Letter', 'Long / Legal', 'Completed jobs', 'Paper jams']]]
    for printer in Printer.objects.all().order_by('name'):
        usage = usage_by_printer[printer.id]
        printer_alerts = printer.alerts.filter(alert_type=Alert.PAPER_JAM)
        if start_date:
            printer_alerts = printer_alerts.filter(created_at__date__gte=start_date)
        if end_date:
            printer_alerts = printer_alerts.filter(created_at__date__lte=end_date)
        jam_count = printer_alerts.count()
        printer_rows.append([
            safe_cell(printer.name),
            safe_cell(f"{usage['total']:,}"),
            safe_cell(f"{usage['A4']:,}"),
            safe_cell(f"{usage['Short']:,}"),
            safe_cell(f"{usage['Long']:,}"),
            safe_cell(f"{usage['jobs']:,}"),
            safe_cell(f'{jam_count:,}'),
        ])
    if len(printer_rows) == 1:
        printer_rows.append([safe_cell('No printer records'), safe_cell('0'), safe_cell('0'), safe_cell('0'), safe_cell('0'), safe_cell('0'), safe_cell('0')])
    story.append(make_table(printer_rows, [content_width * .22, content_width * .13, content_width * .11, content_width * .15, content_width * .15, content_width * .14, content_width * .10]))

    story.append(Paragraph('Print job history', styles['SectionHeading']))
    job_rows = [[safe_cell(label, 'TableHeader') for label in ['Date and time', 'User', 'Printer', 'Pages', 'Paper size', 'Status']]]
    for job in job_history.order_by('-created_at').iterator():
        job_rows.append([safe_cell(timezone.localtime(job.created_at).strftime('%Y-%m-%d %I:%M %p'), 'SmallCell'), safe_cell(job.user_name), safe_cell(job.printer.name), safe_cell(job.pages), safe_cell(job.paper_size), safe_cell(job.status)])
    if len(job_rows) == 1:
        job_rows.append([safe_cell('No print jobs recorded'), safe_cell(''), safe_cell(''), safe_cell(''), safe_cell(''), safe_cell('')])
    story.append(make_table(job_rows, [content_width * .19, content_width * .18, content_width * .24, content_width * .09, content_width * .14, content_width * .12]))

    story.append(Paragraph('Printer error history', styles['SectionHeading']))
    error_rows = [[safe_cell(label, 'TableHeader') for label in ['Date and time', 'Printer', 'Error', 'Details', 'Severity', 'Resolved']]]
    for alert in error_history.order_by('-created_at').iterator():
        error_rows.append([safe_cell(timezone.localtime(alert.created_at).strftime('%Y-%m-%d %I:%M %p'), 'SmallCell'), safe_cell(alert.printer.name if alert.printer else '—'), safe_cell(alert.alert_type), safe_cell(alert.detail, 'SmallCell'), safe_cell(alert.severity), safe_cell('Yes' if alert.is_resolved else 'No')])
    if len(error_rows) == 1:
        error_rows.append([safe_cell('No errors recorded'), safe_cell(''), safe_cell(''), safe_cell(''), safe_cell(''), safe_cell('')])
    story.append(make_table(error_rows, [content_width * .18, content_width * .18, content_width * .19, content_width * .25, content_width * .10, content_width * .10]))

    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#dce2ec'))
        canvas.line(16 * mm, 12 * mm, page_width - 16 * mm, 12 * mm)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#778198'))
        canvas.drawString(16 * mm, 8 * mm, 'PrintPulse · Confidential administrative report')
        canvas.drawRightString(page_width - 16 * mm, 8 * mm, f'Page {doc.page}')
        canvas.restoreState()

    document.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="printpulse-report-{generated_at.date().isoformat()}.pdf"'
    return response
