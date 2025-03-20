from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class BlogPost(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    youtube_title = models.CharField(max_length=255)
    youtube_link = models.URLField()
    generated_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.youtube_title
