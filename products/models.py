from django.db import models


class Product(models.Model):
    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    product_number = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    model_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
    )

    name = models.CharField(max_length=500)

    description = models.TextField(
        blank=True,
        null=True,
    )

    product_category = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    product_sub_category = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    product_type = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    brand = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    product_color = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    materials = models.TextField(
        blank=True,
        null=True,
    )

    image_urls = models.JSONField(default=list)

    raw_data = models.JSONField(default=dict)

    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
    )

    error_message = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_number"]

    def __str__(self):
        return f"{self.product_number} - {self.name}"