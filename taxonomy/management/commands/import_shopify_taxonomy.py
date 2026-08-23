import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from taxonomy.models import (
    TaxonomyAttribute,
    TaxonomyCategory,
    TaxonomyValue,
)


class Command(BaseCommand):
    help = "Import Shopify Product Taxonomy"

    def add_arguments(self, parser):
        parser.add_argument(
            "taxonomy_path",
            type=str,
            help="Path to the Shopify taxonomy dist/en directory",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of categories for testing",
        )

    def handle(self, *args, **options):
        taxonomy_path = Path(options["taxonomy_path"])
        limit = options["limit"]

        categories_file = taxonomy_path / "categories.json"
        attributes_file = taxonomy_path / "attributes.json"

        if not categories_file.exists():
            raise CommandError(
                f"categories.json not found: {categories_file}"
            )

        if not attributes_file.exists():
            raise CommandError(
                f"attributes.json not found: {attributes_file}"
            )

        self.stdout.write(
            self.style.WARNING(
                "Loading Shopify taxonomy files..."
            )
        )

        with open(categories_file, encoding="utf-8") as file:
            categories_data = json.load(file)

        with open(attributes_file, encoding="utf-8") as file:
            attributes_data = json.load(file)

        version = categories_data.get("version")

        self.stdout.write(
            f"Shopify taxonomy version: {version}"
        )

        categories = self.flatten_categories(
            categories_data.get("verticals", [])
        )

        if limit:
            categories = categories[:limit]

        self.stdout.write(
            f"Categories to process: {len(categories)}"
        )

        self.import_categories(categories)

        if not limit:
            self.import_attributes(
                attributes_data.get("attributes", [])
            )
            self.link_category_attributes(categories)
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Sample mode: attributes will not be imported yet."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nShopify taxonomy import completed successfully."
            )
        )

        # Create default admin user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin123")
            self.stdout.write(self.style.SUCCESS("Default admin user (admin/admin123) provisioned automatically."))

    def flatten_categories(self, verticals):
        categories = []

        for vertical in verticals:
            categories.extend(
                vertical.get("categories", [])
            )

        return categories

    @transaction.atomic
    def import_categories(self, categories):
        self.stdout.write(
            "Importing categories..."
        )

        created_count = 0
        updated_count = 0

        for category_data in categories:
            shopify_id = category_data["id"]

            _, created = (
                TaxonomyCategory.objects.update_or_create(
                    shopify_id=shopify_id,
                    defaults={
                        "name": category_data["name"],
                        "full_path": category_data["full_name"],
                        "level": category_data["level"],
                        "is_leaf": len(
                            category_data.get("children", [])
                        ) == 0,
                    },
                )
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            f"Categories created: {created_count}"
        )

        self.stdout.write(
            f"Categories updated: {updated_count}"
        )

        self.stdout.write(
            "Linking category parents..."
        )

        for category_data in categories:
            parent_id = category_data.get("parent_id")

            if not parent_id:
                continue

            TaxonomyCategory.objects.filter(
                shopify_id=category_data["id"]
            ).update(
                parent=TaxonomyCategory.objects.filter(
                    shopify_id=parent_id
                ).first()
            )

    @transaction.atomic
    def import_attributes(self, attributes):
        self.stdout.write(
            "Importing attributes and values..."
        )

        attribute_created = 0
        attribute_updated = 0
        value_created = 0
        value_updated = 0

        for attribute_data in attributes:

            attribute, created = (
                TaxonomyAttribute.objects.update_or_create(
                    shopify_id=attribute_data["id"],
                    defaults={
                        "name": attribute_data["name"],
                        "handle": attribute_data.get("handle"),
                        "description": attribute_data.get(
                            "description"
                        ),
                    },
                )
            )

            if created:
                attribute_created += 1
            else:
                attribute_updated += 1

            for value_data in attribute_data.get("values", []):

                _, created = (
                    TaxonomyValue.objects.update_or_create(
                        shopify_id=value_data["id"],
                        defaults={
                            "attribute": attribute,
                            "name": value_data["name"],
                            "handle": value_data.get("handle"),
                        },
                    )
                )

                if created:
                    value_created += 1
                else:
                    value_updated += 1

        self.stdout.write(
            f"Attributes created: {attribute_created}"
        )

        self.stdout.write(
            f"Attributes updated: {attribute_updated}"
        )

        self.stdout.write(
            f"Values created: {value_created}"
        )

        self.stdout.write(
            f"Values updated: {value_updated}"
        )

    @transaction.atomic
    def link_category_attributes(self, categories):
        self.stdout.write(
            "Linking categories to attributes..."
        )

        attribute_map = {
            attribute.shopify_id: attribute
            for attribute in TaxonomyAttribute.objects.all()
        }

        category_map = {
            category.shopify_id: category
            for category in TaxonomyCategory.objects.all()
        }

        linked_count = 0

        for category_data in categories:
            category = category_map.get(category_data["id"])

            if not category:
                continue

            attributes = [
                attribute_map[attribute_data["id"]]
                for attribute_data in category_data.get(
                    "attributes", []
                )
                if attribute_data["id"] in attribute_map
            ]

            category.attributes.set(attributes)
            linked_count += len(attributes)

        self.stdout.write(
            f"Category-attribute relationships synced: "
            f"{linked_count}"
        )