from django.contrib import admin

from .models import (
    TaxonomyAttribute,
    TaxonomyCategory,
    TaxonomyValue,
)


@admin.register(TaxonomyCategory)
class TaxonomyCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "shopify_id",
        "name",
        "parent",
        "level",
        "is_leaf",
    )

    search_fields = (
        "shopify_id",
        "name",
        "full_path",
    )

    list_filter = (
        "is_leaf",
        "level",
    )


@admin.register(TaxonomyAttribute)
class TaxonomyAttributeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "handle",
        "shopify_id",
    )

    search_fields = (
        "name",
        "handle",
        "shopify_id",
    )

    filter_horizontal = (
        "categories",
    )


@admin.register(TaxonomyValue)
class TaxonomyValueAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "attribute",
        "handle",
        "shopify_id",
    )

    search_fields = (
        "name",
        "handle",
        "shopify_id",
    )