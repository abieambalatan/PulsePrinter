from django.contrib import admin

from .models import Alert, PaperUsage, PrintJob, Printer


admin.site.register(Printer)
admin.site.register(PrintJob)
admin.site.register(PaperUsage)
admin.site.register(Alert)

admin.site.site_header = 'PrintPulse Admin Office'
admin.site.site_title = 'PrintPulse Administration'
admin.site.index_title = 'Manage your printing workspace'
