from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Business, BusinessAccess, Holding, Role, RolePermission, User

admin.site.register(Holding)
admin.site.register(Business)
admin.site.register(Role)
admin.site.register(RolePermission)
admin.site.register(BusinessAccess)
admin.site.register(User, UserAdmin)
