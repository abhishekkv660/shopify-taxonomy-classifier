from django.contrib import admin

from .models import (
    AlternativeCategory,
    Classification,
    ClassificationAttribute,
)


@admin.register(Classification)
class ClassificationAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "predicted_category",
        "confidence",
        "status",
        "requires_manual_review",
    )

    list_filter = (
        "status",
        "requires_manual_review",
    )

    search_fields = (
        "product__product_number",
        "product__name",
    )


@admin.register(ClassificationAttribute)
class ClassificationAttributeAdmin(admin.ModelAdmin):
    list_display = (
        "classification",
        "attribute",
        "value",
        "confidence",
    )


@admin.register(AlternativeCategory)
class AlternativeCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "classification",
        "category",
        "confidence",
        "rank",
    )