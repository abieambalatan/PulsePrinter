from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='printjob',
            name='source_machine',
            field=models.CharField(blank=True, default='', max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='printjob',
            name='source_event_id',
            field=models.CharField(blank=True, default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='alert',
            name='source_machine',
            field=models.CharField(blank=True, default='', max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='alert',
            name='source_event_id',
            field=models.CharField(blank=True, default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='printjob',
            name='paper_size',
            field=models.CharField(
                choices=[
                    ('A4', 'A4'),
                    ('Short', 'Short / Letter'),
                    ('Long', 'Long / Legal'),
                    ('Unknown', 'Unknown'),
                ],
                default='A4',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='paperusage',
            name='paper_size',
            field=models.CharField(
                choices=[
                    ('A4', 'A4'),
                    ('Short', 'Short / Letter'),
                    ('Long', 'Long / Legal'),
                    ('Unknown', 'Unknown'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name='printjob',
            constraint=models.UniqueConstraint(
                condition=~Q(source_event_id=''),
                fields=('source_machine', 'source_event_id'),
                name='unique_print_event_source',
            ),
        ),
        migrations.AddConstraint(
            model_name='alert',
            constraint=models.UniqueConstraint(
                condition=~Q(source_event_id=''),
                fields=('source_machine', 'source_event_id'),
                name='unique_alert_event_source',
            ),
        ),
    ]
