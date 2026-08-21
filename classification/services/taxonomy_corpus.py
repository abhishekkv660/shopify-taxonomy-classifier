from taxonomy.models import TaxonomyCategory


def build_category_document(category):
    """
    Build a searchable document representing a Shopify taxonomy category.
    """

    parts = [
        category.name,
        category.full_path,
    ]

    return " ".join(
        part
        for part in parts
        if part
    )


def get_category_corpus():
    """
    Build a searchable corpus from Shopify taxonomy categories.

    Includes both parent and leaf categories so that products are not
    forced into an overly specific leaf category when the available
    product information does not support that specificity.
    """

    categories = (
        TaxonomyCategory.objects
        .all()
        .order_by("full_path")
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


def get_leaf_category_corpus():
    """
    Backward-compatible helper for leaf-only category retrieval.
    """

    categories = (
        TaxonomyCategory.objects
        .filter(is_leaf=True)
        .order_by("full_path")
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