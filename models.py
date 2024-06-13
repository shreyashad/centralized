from django.db import models

# Create your models here.

class ApplicationPermission(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    application = models.CharField(max_length=100)

    def __str__(self):
        return self.name



class Role(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    permissions = models.ManyToManyField(ApplicationPermission)

    def __str__(self):
        return self.name