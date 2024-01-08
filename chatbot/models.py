from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib import auth


# Create your models here.

class Patient(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    alias = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=100, blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=100, blank=True, null=True)
    first_time = models.BooleanField(default=True)
    previous_diagnosis = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return self.alias

class Session(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    date = models.DateTimeField()
    def __str__(self):
        return f"Session with {self.patient.alias} at {str(self.date)}"

class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    timestamp = models.DateTimeField(default=timezone.now)
    conversation = models.JSONField(default=list)  # Store conversation history as a list of JSON objects
    session = models.ForeignKey(Session, on_delete=models.CASCADE, default=None, blank=True, null=True)
    is_open = models.BooleanField(default=True)
    def __str__(self):
        if self.session:
            return f"session arranged with {Patient.objects.get(user=self.user).alias} at {str(self.session.date)} "
        else:
            return f"Chat with {self.user} at {str(self.timestamp)}"
    def add_message(self, role, content, visible = True):
        self.conversation.append({"role": role, "content": content, "visible": visible, "timestamp": str(timezone.now())})
        self.save()