from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "product_number",
        "model_number",
        "name",
        "product_category",
        "product_sub_category",
        "processing_status",
    )

    search_fields = (
        "product_number",
        "model_number",
        "name",
    )

    list_filter = (
        "product_category",
        "processing_status",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )