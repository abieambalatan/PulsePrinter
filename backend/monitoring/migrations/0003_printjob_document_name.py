from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0002_printjob_alert_source_events'),
    ]

    operations = [
        migrations.AddField(
            model_name='printjob',
            name='document_name',
            field=models.CharField(blank=True, default='', max_length=255),
            preserve_default=False,
        ),
    ]
