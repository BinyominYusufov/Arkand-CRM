from django.contrib import admin

from .models import Employee, PayrollItem, PayrollRun, SalaryScheme

admin.site.register(Employee)
admin.site.register(SalaryScheme)
admin.site.register(PayrollRun)
admin.site.register(PayrollItem)
