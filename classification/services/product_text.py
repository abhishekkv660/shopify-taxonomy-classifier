import re

from products.models import Product


def normalize_text(value: str) -> str:
    """
    Normalize text for category classification.
    """
    if not value:
        return ""

    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def build_product_text(product: Product) -> str:
    """
    Build a weighted text representation of a product.

    Product name is repeated because it is generally the
    strongest signal for taxonomy classification.
    """

    parts = []

    if product.name:
        # Higher importance
        parts.extend([product.name] * 3)

    if product.product_type:
        parts.extend([product.product_type] * 2)

    if product.product_sub_category:
        parts.extend([product.product_sub_category] * 2)

    if product.product_category:
        parts.append(product.product_category)

    if product.materials:
        parts.append(product.materials)

    if product.description:
        parts.append(product.description)

    return normalize_text(" ".join(parts))