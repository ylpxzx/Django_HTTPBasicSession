from django.contrib import admin
from .models import *
# Register your models here.


class UserAdmin(admin.ModelAdmin):
    list_display = ('name','sex','email','password','c_time')
    list_filter = ['sex','name','c_time']
    search_fields = ['sex','name','c_time']

class ConfirmAdmin(admin.ModelAdmin):
    list_display = ('code','user','c_time')
admin.site.register(User,UserAdmin)
admin.site.register(ConfirmString,ConfirmAdmin)