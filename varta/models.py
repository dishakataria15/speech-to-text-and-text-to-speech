from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    translated_message = models.TextField(blank=True)
    source_language = models.CharField(max_length=10, default='en')
    target_language = models.CharField(max_length=10, default='hi')
    message_type = models.CharField(max_length=20, choices=[
        ('text', 'Text'),
        ('speech', 'Speech'),
        ('quick_response', 'Quick Response')
    ], default='text')
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}"

class QuickResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    phrase = models.TextField()
    language = models.CharField(max_length=10, default='en')
    category = models.CharField(max_length=50, default='General')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.phrase[:50]}"