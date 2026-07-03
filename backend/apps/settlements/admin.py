from django.contrib import admin

from .models import Barter, Debt, DebtSettlement, Transfer

admin.site.register(Transfer)
admin.site.register(Debt)
admin.site.register(DebtSettlement)
admin.site.register(Barter)
