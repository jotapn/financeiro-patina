from django.contrib import admin

from .models import RecurrenceRule, Tag, Transaction

admin.site.register(Transaction)
admin.site.register(Tag)
admin.site.register(RecurrenceRule)

