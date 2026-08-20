from django.db import models


class ProcessingJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        PAUSED = "paused", "Paused"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    total_products = models.PositiveIntegerField(default=0)

    pending_products = models.PositiveIntegerField(default=0)

    processing_products = models.PositiveIntegerField(default=0)

    completed_products = models.PositiveIntegerField(default=0)

    failed_products = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.id} - {self.status}"