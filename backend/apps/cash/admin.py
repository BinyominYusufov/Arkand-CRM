from django.contrib import admin

from .models import CashOperation, CashRegister

admin.site.register(CashRegister)
admin.site.register(CashOperation)
