from django.db import models
from django.contrib.auth.models import User


class TempAssignation(models.Model):
    demander = models.ForeignKey(User, related_name="demander", on_delete=models.CASCADE)
    date_demand = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    last_name = models.CharField(null=True, max_length=200)
    first_name = models.CharField(null=True, max_length=200)
