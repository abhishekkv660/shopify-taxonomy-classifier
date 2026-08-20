from django.contrib import admin

from .models import ProcessingJob


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "total_products",
        "pending_products",
        "processing_products",
        "completed_products",
        "failed_products",
        "created_at",
    )

    list_filter = (
        "status",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
    )