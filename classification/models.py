from django.db import models

from products.models import Product
from taxonomy.models import TaxonomyAttribute, TaxonomyCategory


class Classification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        APPROVED = "approved", "Approved"
        MANUALLY_UPDATED = "manually_updated", "Manually Updated"

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="classification",
    )

    predicted_category = models.ForeignKey(
        TaxonomyCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classifications",
    )

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    requires_manual_review = models.BooleanField(
        default=False,
        db_index=True,
    )

    failure_reason = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        category = self.predicted_category or "No category"
        return f"{self.product.product_number} - {category}"


class ClassificationAttribute(models.Model):
    classification = models.ForeignKey(
        Classification,
        on_delete=models.CASCADE,
        related_name="attributes",
    )

    attribute = models.ForeignKey(
        TaxonomyAttribute,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classification_attributes",
    )

    value = models.CharField(
        max_length=500,
    )

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["classification", "attribute", "value"],
                name="unique_classification_attribute_value",
            )
        ]

    def __str__(self):
        attribute_name = self.attribute.name if self.attribute else "Unknown"
        return f"{attribute_name}: {self.value}"


class AlternativeCategory(models.Model):
    classification = models.ForeignKey(
        Classification,
        on_delete=models.CASCADE,
        related_name="alternative_categories",
    )

    category = models.ForeignKey(
        TaxonomyCategory,
        on_delete=models.CASCADE,
        related_name="alternative_classifications",
    )

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
    )

    rank = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["classification", "rank"],
                name="unique_alternative_category_rank",
            )
        ]

    def __str__(self):
        return f"{self.rank}. {self.category}"