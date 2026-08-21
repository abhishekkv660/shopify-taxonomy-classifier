from taxonomy.models import TaxonomyCategory

from classification.services.product_text import normalize_text


def build_category_document(category: TaxonomyCategory) -> str:
    """
    Build a searchable text representation of a Shopify taxonomy category.

    The leaf category name is repeated because it is the most specific
    classification signal, while the full path provides hierarchical context.
    """

    leaf_name = category.name or ""
    full_path = category.full_path or ""

    parts = [
        leaf_name,
        leaf_name,
        full_path,
    ]

    return normalize_text(" ".join(parts))


def get_leaf_category_corpus():
    """
    Return all Shopify leaf categories and their searchable documents.

    Each item contains:
        - category: TaxonomyCategory instance
        - text: normalized searchable document
    """

    categories = TaxonomyCategory.objects.filter(
        is_leaf=True
    ).only(
        "id",
        "name",
        "full_path",
        "shopify_id",
    )

    corpus = []

    for category in categories:
        corpus.append(
            {
                "category": category,
                "text": build_category_document(category),
            }
        )

    return corpus