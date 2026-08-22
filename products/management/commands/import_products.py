import math
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from products.models import Product


class Command(BaseCommand):
    help = "Import products from an Excel file"

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path",
            type=str,
            help="Path to the product Excel file",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of rows to import",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file_path"])
        limit = options["limit"]

        if not file_path.exists():
            raise CommandError(
                f"File does not exist: {file_path}"
            )

        try:
            dataframe = pd.read_excel(file_path)
        except Exception as exc:
            raise CommandError(
                f"Unable to read Excel file: {exc}"
            ) from exc

        if limit:
            dataframe = dataframe.head(limit)

        total_rows = len(dataframe)

        created_count = 0
        updated_count = 0
        skipped_count = 0

        self.stdout.write(
            f"Found {total_rows} rows to process."
        )

        for index, row in dataframe.iterrows():
            try:
                product_data = self.normalize_row(row)

                if not product_data["product_number"]:
                    skipped_count += 1

                    self.stderr.write(
                        f"Row {index + 2}: skipped because "
                        "Product Number is missing."
                    )

                    continue

                with transaction.atomic():
                    _, created = Product.objects.update_or_create(
                        product_number=product_data["product_number"],
                        defaults=product_data,
                    )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as exc:
                skipped_count += 1

                self.stderr.write(
                    f"Row {index + 2}: failed - {exc}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "\nImport completed:"
                f"\nCreated: {created_count}"
                f"\nUpdated: {updated_count}"
                f"\nSkipped/Failed: {skipped_count}"
            )
        )

    def normalize_row(self, row):
        raw_data = {
            str(column).strip(): self.clean_value(value)
            for column, value in row.items()
        }

        image_urls = self.extract_image_urls(raw_data)

        return {
            "product_number": self.clean_value(raw_data.get("Product Number")),
            "model_number": self.clean_value(raw_data.get("Model Number")),
            "name": self.clean_value(raw_data.get("Product Name")),
            "description": self.clean_value(raw_data.get("Product Description")),
            "product_category": self.clean_value(raw_data.get("Product Category")),
            "product_sub_category": self.clean_value(raw_data.get("Product Sub Category")),
            "product_type": None,
            "brand": None,
            "product_color": self.clean_value(raw_data.get("Product Color")),
            "materials": self.clean_value(raw_data.get("Materials")),
            "image_urls": image_urls,
            "raw_data": raw_data,
        }

    def extract_image_urls(self, row):
        image_urls = []

        for number in range(1, 21):
            column_name = f"Image {number}"
            value = self.clean_value(row.get(column_name))

            if value:
                image_urls.append(value)

        return image_urls

    def clean_value(self, value):
        if value is None:
            return None

        if isinstance(value, float) and math.isnan(value):
            return None

        value = str(value).strip()

        return value or None