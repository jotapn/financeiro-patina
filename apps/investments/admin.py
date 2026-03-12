from django.contrib import admin

from .models import AssetClass, Investment, InvestmentGoal, InvestmentTransaction

admin.site.register(AssetClass)
admin.site.register(Investment)
admin.site.register(InvestmentTransaction)
admin.site.register(InvestmentGoal)
