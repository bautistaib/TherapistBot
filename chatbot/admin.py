from django.contrib import admin
from .models import Patient, Chat, Session

admin.site.register(Patient)
admin.site.register(Chat)
admin.site.register(Session)
# Register your models here.
