# from pandas.core.indexes import category
from django.utils import termcolors
import re

from sklearn.feature_extraction.text import (
    ENGLISH_STOP_WORDS,
    TfidfVectorizer,
)
from sklearn.metrics.pairwise import cosine_similarity

from classification.services.product_text import normalize_text
from classification.services.taxonomy_corpus import get_category_corpus
from products.models import Product


class CategoryCandidateRetriever:
    """
    Retrieve Shopify taxonomy category candidates using
    field-aware TF-IDF similarity followed by structured
    product-aware reranking.
    """

    FIELD_WEIGHTS = {
        "name": 0.40,
        "product_type": 0.20,
        "product_sub_category": 0.20,
        "product_category": 0.15,
        "description": 0.04,
        "materials": 0.01,
    }

    CONCEPT_MATCH_BOOST = 0.08
    SUBCATEGORY_MATCH_BOOST = 0.12
    ACCESSORY_PENALTY = 0.10
    UNSUPPORTED_SPECIFICITY_PENALTY = 0.08
    # UNSUPPORTED_CONCEPT_PENALTY = 0.15
    IDENTITY_MISMATCH_PENALTY = 0.10
    MODIFIER_MISMATCH_PENALTY = 0.10
    MIN_RAW_SCORE = 0.01
    MIN_FINAL_SCORE = 0.02
    NAME_IDENTITY_BOOST = 0.20
    PRIMARY_TERM_OVERLAP_BOOST = 0.04

    MODIFIER_TERMS = {
        "outdoor",
        "indoor",
        "corner",
        "sectional",
        "loveseat",
        "play",
        "baby",
        "toddler",
        "storage",
        "wall",
        "floor",
    }
    ACCESSORY_TERMS = {
        "accessories",
        "accessory",
        "legs",
        "supports",
        "cushions",
        "covers",
        "throws",
        "replacement",
        "parts",
    }

    PRODUCT_TYPE_TERMS = {
        "sofa",
        "chair",
        "armchair",
        "recliner",
        "stool",
        "table",
        "bed",
        "desk",
        "cabinet",
        "leg",
        "legs",
        "cushion",
        "throw",
        "ottoman",
    }
    MATERIAL_TERMS = {
        "leather",
        "bonded",
        "wood",
        "metal",
        "steel",
        "plastic",
        "glass",
        "fabric",
        "cotton",
        "wool",
        "linen",
        "polyester",
        "velvet",
        "rubber",
    }
    TERM_ALIASES = {
    "bin": {
        "bin",
        "can",
        "wastebasket",
    },
    "can": {
        "bin",
        "can",
        "wastebasket",
    },
    "wastebasket": {
        "bin",
        "can",
        "wastebasket",
    },

    "pencil": {
        "pencil",
        "pen",
    },
    "pen": {
        "pencil",
        "pen",
    },

    "holder": {
        "holder",
        "organizer",
    },
    }
    COMPOUND_PRODUCT_CONCEPTS = {
        frozenset({"trash", "bin"}): {
            "trash",
            "can",
            "wastebasket",
        },

        frozenset({"pencil", "holder"}): {
            "pen",
            "holder",
            "desk",
            "organizer",
        },
    }
    def _prepare_tfidf_text(self, text):
        """
        Normalize text for TF-IDF so product and taxonomy
        terms use the same representation.

        Example:
            "Ottomans" -> "ottoman"
            "Sofa Tables" -> "sofa table"
        """

        normalized = normalize_text(text or "")

        raw_terms = re.findall(
            r"\b[a-z0-9]+\b",
            normalized,
        )

        normalized_terms = [
            self._normalize_term(term)
            for term in raw_terms
            if term not in ENGLISH_STOP_WORDS
            and len(term) > 2
        ]

        return " ".join(normalized_terms)

    def __init__(self):
        self.corpus = get_category_corpus()

        self.documents = [
            self._prepare_tfidf_text(
                item["text"]
            )
            for item in self.corpus
        ]

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
        )

        self.category_matrix = self.vectorizer.fit_transform(
            self.documents
        )

    def _get_field_similarity(self, value):
        """
        Calculate similarity between one product field and
        all taxonomy category documents.
        """

        normalized_value = self._prepare_tfidf_text(
            value or ""
        )

        if not normalized_value:
            return None

        vector = self.vectorizer.transform(
            [normalized_value]
        )

        return cosine_similarity(
            vector,
            self.category_matrix,
        ).flatten()

    def _normalize_term(self, term):
        """
        Apply simple normalization so singular and plural forms
        are treated as the same concept.
        """

        if term.endswith("ies") and len(term) > 4:
            return term[:-3] + "y"

        if term.endswith("s") and not term.endswith("ss"):
            return term[:-1]

        return term
        
    def _expand_terms(self, terms):
        """
        Expand product terms using known taxonomy aliases.
        """

        expanded = set(terms)

        for term in terms:
            aliases = self.TERM_ALIASES.get(term)

            if aliases:
                expanded.update(aliases)

        return expanded
    def _expand_compound_product_concepts(
        self,
        terms,
    ):
        """
        Expand known multi-word product concepts.

        Example:
            {'trash', 'bin'}
            -> {'trash', 'bin', 'can', 'wastebasket'}
        """

        expanded_terms = set(terms)

        for concept_terms, additions in (
            self.COMPOUND_PRODUCT_CONCEPTS.items()
        ):
            if concept_terms.issubset(terms):
                expanded_terms.update(additions)

        return expanded_terms
    def _extract_terms(self, text):
        """
        Extract meaningful normalized terms.
        """

        normalized = normalize_text(text or "")

        terms = re.findall(
            r"\b[a-z0-9]+\b",
            normalized,
        )

        return {
            self._normalize_term(term)
            for term in terms
            if term not in ENGLISH_STOP_WORDS
            and len(term) > 2
        }
    def _extract_product_identity_terms(self, product):
        """
        Extract the strongest product identity terms from the
        product name.

        The product name usually contains the most specific
        information about what the actual object is.
        """

        if not product.name:
            return set()

        name_terms = self._extract_terms(product.name)

        # Remove common brand / descriptive words that should
        # not define the product taxonomy identity.
        ignored_terms = {
            "by",
            "with",
            "and",
            "for",
            "the",
            "modway",
            "upholstered",
            "bonded",
            "leather",
            "fabric",
            "vinyl",
            "wood",
            "round",
            "highback",
        }

        return name_terms - ignored_terms

    def _get_category_identity_terms(
        self,
        category,
    ):
        """
        Extract the primary product identity from the leaf category.

        Examples:
            Sofas -> {"sofa"}
            Armchairs -> {"armchair"}
            Sofa Tables -> {"table"}
            Sofa Legs -> {"leg"}
            Sofa Beds -> {"sofa", "bed"}
        """

        normalized = normalize_text(
            category.name or ""
        )

        raw_terms = re.findall(
            r"\b[a-z0-9]+\b",
            normalized,
        )

        ordered_terms = [
            self._normalize_term(term)
            for term in raw_terms
            if term not in ENGLISH_STOP_WORDS
            and len(term) > 2
        ]

        identity_terms = [
            term
            for term in ordered_terms
            if term in self.PRODUCT_TYPE_TERMS
        ]

        if not identity_terms:
            return set()

        # "Sofa Beds" represents a sofa with a bed function,
        # so preserve both identities for later specificity logic.
        if (
            "sofa" in identity_terms
            and "bed" in identity_terms
        ):
            return {"sofa", "bed"}

        # For compound categories, the final product-type noun
        # is treated as the primary identity.
        #
        # Sofa Tables -> table
        # Sofa Legs -> leg
        return {identity_terms[-1]}

    def _calculate_product_identity_penalty(
        self,
        product,
        category,
    ):
        """
        Penalize categories that do not contain the product's
        strongest identity concept.
        """

        identity_terms = (
            self._extract_product_identity_terms(product)
        )

        if not identity_terms:
            return 0.0

        category_terms = self._extract_terms(
            category.full_path
        )

        important_identity_terms = {
            "sofa",
            "armchair",
            "ottoman",
            "chair",
            "stool",
            "table",
            "desk",
            "bed",
            "cabinet",
            "shelf",
        }

        product_identity = (
            identity_terms
            & important_identity_terms
        )

        if not product_identity:
            return 0.0

        category_identity = (
            category_terms
            & important_identity_terms
        )

        if not category_identity:
            return 0.0

        if product_identity & category_identity:
            return 0.0

        return self.IDENTITY_MISMATCH_PENALTY
    def _get_primary_terms(self, product):
        """
        Extract meaningful product identity terms.

        Material and descriptive terms are removed so that
        they do not incorrectly boost unrelated categories.
        """

        primary_parts = []

        if product.product_type:
            primary_parts.append(
                product.product_type
            )

        if product.product_sub_category:
            primary_parts.append(
                product.product_sub_category
            )

        if product.name:
            primary_parts.append(
                product.name
            )

        primary_terms = self._extract_terms(
            " ".join(primary_parts)
        )

        normalized_terms = set()

        for term in primary_terms:
            normalized = self._normalize_term(term)

            if isinstance(normalized, set):
                normalized_terms.update(normalized)
            elif normalized:
                normalized_terms.add(normalized)

        material_terms = (
            self._extract_terms(
                product.materials or ""
            )
            | self.MATERIAL_TERMS
        )

        primary_terms = (
            normalized_terms - material_terms
        )

        return self._expand_compound_product_concepts(
            primary_terms
        )

    def _get_product_name_terms(self, product):
        """
        Extract meaningful identity terms directly from the
        product name.
        """

        return self._extract_terms(
            product.name or ""
        )
    def _calculate_primary_term_overlap_boost(
        self,
        primary_terms,
        category,
    ):
        """
        Boost categories that have meaningful overlap with
        the product's expanded primary terms.
        """

        category_terms = self._extract_terms(
            category.full_path
        )

        overlap = primary_terms & category_terms

        if not overlap:
            return 0.0

        return min(
            len(overlap) * self.PRIMARY_TERM_OVERLAP_BOOST,
            0.12,
        )
    
    def _calculate_concept_boost(
        self,
        product_name_terms,
        category,
    ):
        """
        Boost categories that match concepts explicitly present
        in the product name.
        """

        category_terms = self._extract_terms(
            category.full_path
        )

        matched_terms = (
            product_name_terms & category_terms
        )

        return (
            len(matched_terms)
            * self.CONCEPT_MATCH_BOOST
        )

    def _calculate_subcategory_boost(
        self,
        product,
        category,
    ):
        """
        Compare the product subcategory directly with the
        taxonomy category path.

        This gives structured source data additional
        influence during reranking.
        """

        if not product.product_sub_category:
            return 0.0

        product_terms = self._extract_terms(
            product.product_sub_category
        )

        category_terms = self._extract_terms(
            category.full_path
        )

        matched_terms = (
            product_terms & category_terms
        )

        if not product_terms:
            return 0.0

        match_ratio = (
            len(matched_terms)
            / len(product_terms)
        )

        return (
            match_ratio
            * self.SUBCATEGORY_MATCH_BOOST
        )

    def _is_accessory_category(
        self,
        category,
    ):
        """
        Return True when the category represents an accessory,
        part, or related item rather than the primary product.
        """

        category_terms = self._extract_terms(
            category.full_path
        )

        return bool(
            category_terms & self.ACCESSORY_TERMS
        )

    def _calculate_name_identity_boost(
        self,
        product_name_terms,
        category,
    ):
        """
        Boost a category when the actual product identity
        matches the category's actual identity.
        """

        if self._is_accessory_category(category):
            return 0.0

        product_identities = (
            product_name_terms
            & self.PRODUCT_TYPE_TERMS
        )

        if not product_identities:
            return 0.0

        category_identities = (
            self._get_category_identity_terms(
                category
            )
        )

        if not category_identities:
            return 0.0

        matched_identities = (
            product_identities
            & category_identities
        )

        if not matched_identities:
            return 0.0

        return self.NAME_IDENTITY_BOOST
        
    
    
    def _calculate_accessory_penalty(
        self,
        product,
        category,
    ):
        """
        Penalize accessory categories when the product itself
        does not appear to be an accessory.
        """

        product_text = " ".join(
            filter(
                None,
                [
                    product.name,
                    product.product_type,
                    product.product_sub_category,
                ],
            )
        )

        product_terms = self._extract_terms(
            product_text
        )

        category_is_accessory = (
            self._is_accessory_category(
                category
            )
        )

        product_is_accessory = bool(
            product_terms & self.ACCESSORY_TERMS
        )

        if (
            category_is_accessory
            and not product_is_accessory
        ):
            return self.ACCESSORY_PENALTY

        return 0.0

    # def _calculate_identity_penalty(
    #     self,
    #     product_name_terms,
    #     category,
    # ):
    #     """
    #     Penalize categories whose product identity conflicts
    #     with the identity expressed in the product name.

    #     Example:
    #         Product: Leather Sofa
    #         Category: Sofa Tables

    #     The product is a sofa, not a table.
    #     """

    #     product_identities = (
    #         product_name_terms
    #         & self.PRODUCT_TYPE_TERMS
    #     )

    #     if not product_identities:
    #         return 0.0

    #     category_terms = self._extract_terms(
    #         category.full_path
    #     )

    #     category_identities = (
    #         category_terms
    #         & self.PRODUCT_TYPE_TERMS
    #     )

    #     if not category_identities:
    #         return 0.0

    #     conflicting_identities = (
    #         category_identities
    #         - product_identities
    #     )

    #     return (
    #         len(conflicting_identities)
    #         * self.IDENTITY_MISMATCH_PENALTY
    #     )


    def _calculate_modifier_penalty(
        self,
        product_terms,
        category,
    ):
        """
        Penalize categories that contain explicit contextual modifiers
        not supported by the product.

        Example:
            Product: "Leather Sofa"
            Category: "Outdoor Sofas"

            → "outdoor" is unsupported
            → apply modifier penalty
        """

        category_terms = self._extract_terms(
            category.full_path
        )

        category_modifiers = (
            category_terms
            & self.MODIFIER_TERMS
        )

        unsupported_modifiers = (
            category_modifiers
            - product_terms
        )

        if not unsupported_modifiers:
            return 0.0

        return (
            len(unsupported_modifiers)
            * self.MODIFIER_MISMATCH_PENALTY
        )

    def _get_new_category_terms(self, category):
        """
        Return meaningful terms introduced by the current category
        compared with its parent category.
        """

        category_terms = self._extract_terms(
            category.full_path
        )

        if category.parent is None:
            return set()

        parent_terms = self._extract_terms(
            category.parent.full_path
        )

        return category_terms - parent_terms


    def _calculate_specificity_penalty(
        self,
        primary_terms,
        category,
    ):
        """
        Penalize categories that introduce new concepts not
        supported by the product identity.
        """

        new_category_terms = (
            self._get_new_category_terms(category)
        )

        unsupported_terms = [
            term
            for term in new_category_terms
            if term not in primary_terms
        ]

        return (
            len(unsupported_terms)
            * self.UNSUPPORTED_SPECIFICITY_PENALTY
        )

    # def _calculate_unsupported_concept_penalty(
    #     self,
    #     primary_terms,
    #     category,
    # ):
    #     """
    #     Penalize important category concepts that are not
    #     supported by the product identity.
    #     """

    #     category_terms = self._extract_terms(
    #         category.full_path
    #     )

    #     unsupported_terms = (
    #         category_terms - primary_terms
    #     )

    #     ignored_terms = {
    #         "furniture",
    #         "home",
    #         "garden",
    #         "good",
    #         "supply",
    #         "supplies",
    #         "item",
    #         "items",
    #     }

    #     unsupported_terms -= ignored_terms

    #     return (
    #         len(unsupported_terms)
    #         * self.UNSUPPORTED_CONCEPT_PENALTY
    #     )

    def retrieve(self, product: Product, top_k: int = 5):
        """
        Return top-k taxonomy categories using:

        1. Weighted field-level TF-IDF similarity.
        2. Product concept boosting.
        3. Product subcategory matching.
        4. Accessory mismatch penalties.
        5. Unsupported specificity penalties.
        """

        total_scores = None

        for field_name, weight in self.FIELD_WEIGHTS.items():

            field_value = getattr(
                product,
                field_name,
                None,
            )

            similarities = self._get_field_similarity(
                field_value
            )

            if similarities is None:
                continue

            weighted_scores = similarities * weight

            if total_scores is None:
                total_scores = weighted_scores
            else:
                total_scores += weighted_scores

        if total_scores is None:
            return []

        primary_terms = self._get_primary_terms(
            product
        )

        product_name_terms = self._extract_terms(
            product.name or ""
        )

        adjusted_scores = total_scores.copy()

        score_details = []
        for index, item in enumerate(self.corpus):

            category = item["category"]

            concept_boost = (
                self._calculate_concept_boost(
                    product_name_terms,
                    category,
                )
            )

            subcategory_boost = (
                self._calculate_subcategory_boost(
                    product,
                    category,
                )
            )

            accessory_penalty = (
                self._calculate_accessory_penalty(
                    product,
                    category,
                )
            )
            specificity_penalty = (
                self._calculate_specificity_penalty(
                    primary_terms,
                    category,
                )
            )

            identity_penalty = (
                self._calculate_product_identity_penalty(
                    product,
                    category,
                )
            )

            modifier_penalty = (
                self._calculate_modifier_penalty(
                    primary_terms,
                    category,
                )
            )
            name_identity_boost = (
                self._calculate_name_identity_boost(
                    product_name_terms,
                    category,
                )
            )
            primary_term_overlap_boost = (
                self._calculate_primary_term_overlap_boost(
                    primary_terms,
                    category,
                )
            )
            
            # unsupported_concept_penalty = (
            #     self._calculate_unsupported_concept_penalty(
            #         primary_terms,
            #         category,
            #     )
            # )

            adjusted_scores[index] += concept_boost
            adjusted_scores[index] += subcategory_boost
            adjusted_scores[index] += primary_term_overlap_boost
            adjusted_scores[index] += name_identity_boost
            adjusted_scores[index] -= accessory_penalty
            adjusted_scores[index] -= specificity_penalty
            # adjusted_scores[index] -= unsupported_concept_penalty
            adjusted_scores[index] -= identity_penalty
            adjusted_scores[index] -= modifier_penalty
            

            score_details.append(
                {
                    "concept_boost": concept_boost,
                    "subcategory_boost": subcategory_boost,
                    "accessory_penalty": accessory_penalty,
                    "specificity_penalty": specificity_penalty,
                    # "unsupported_concept_penalty": (
                    #     unsupported_concept_penalty
                    # ),
                    "primary_term_overlap_boost": primary_term_overlap_boost,
                    "identity_penalty": identity_penalty,
                    "modifier_penalty": modifier_penalty,
                    "name_identity_boost": name_identity_boost,
                }
            )

        valid_indices = [
            index
            for index, raw_score in enumerate(total_scores)
            if (
                raw_score >= self.MIN_RAW_SCORE
                and adjusted_scores[index] >= self.MIN_FINAL_SCORE
            )
        ]
        valid_indices.sort(
            key=lambda index: adjusted_scores[index],
            reverse=True,
        )
        top_indices = valid_indices[:top_k]

        results = []

        for rank, index in enumerate(
            top_indices,
            start=1,
        ):
            item = self.corpus[index]

            results.append(
                {
                    "rank": rank,
                    "category": item["category"],
                    "score": float(
                        adjusted_scores[index]
                    ),
                    "raw_score": float(
                        total_scores[index]
                    ),
                    **score_details[index],
                }
            )

        return results