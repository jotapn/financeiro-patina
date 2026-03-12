from django.contrib import admin

from .models import CardInvoice, CreditCard

admin.site.register(CreditCard)
admin.site.register(CardInvoice)

