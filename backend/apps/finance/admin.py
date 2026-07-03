from django.contrib import admin

from .models import ExpenseCategory, Transaction

admin.site.register(ExpenseCategory)
admin.site.register(Transaction)
