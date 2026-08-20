from django.db import models


class TaxonomyCategory(models.Model):
    shopify_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    name = models.CharField(
        max_length=500,
        db_index=True,
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    full_path = models.TextField(
        unique=True,
    )

    level = models.PositiveSmallIntegerField(
        default=0,
    )

    is_leaf = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["full_path"]

    def __str__(self):
        return self.full_path


class TaxonomyAttribute(models.Model):
    shopify_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )

    name = models.CharField(
        max_length=255,
        db_index=True,
    )

    handle = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    categories = models.ManyToManyField(
        TaxonomyCategory,
        related_name="attributes",
        blank=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TaxonomyValue(models.Model):
    shopify_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )

    attribute = models.ForeignKey(
        TaxonomyAttribute,
        on_delete=models.CASCADE,
        related_name="values",
    )

    name = models.CharField(
        max_length=500,
    )

    handle = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        db_index=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.attribute.name}: {self.name}"