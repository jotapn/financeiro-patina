from django.db import models


class Investment(models.Model):
    family_group = models.ForeignKey('core.FamilyGroup', on_delete=models.CASCADE, related_name='investments')
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

