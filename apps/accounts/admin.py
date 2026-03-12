from django.contrib import admin

from .models import FinancialAccount, PaymentMethod

admin.site.register(FinancialAccount)
admin.site.register(PaymentMethod)

