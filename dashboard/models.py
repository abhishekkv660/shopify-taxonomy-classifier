from django.db import models

class ProcessingJob(models.Model):
    """
    Tracks a background Celery batch job processing unclassified products.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    total_products = models.IntegerField(default=0)
    completed = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    pending = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    error_information = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Job #{self.id} - {self.status} ({self.completed}/{self.total_products})"

    @property
    def progress_percentage(self):
        if self.total_products == 0:
            return 0
        return int(((self.completed + self.failed) / self.total_products) * 100)
