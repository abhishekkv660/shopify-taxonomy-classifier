from rest_framework import serializers
from classification.models import Classification, ClassificationAttribute, AlternativeCategory
from products.models import Product

class ClassificationAttributeSerializer(serializers.ModelSerializer):
    attribute_name = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    
    class Meta:
        model = ClassificationAttribute
        fields = ['id', 'attribute_name', 'value', 'confidence']

    def get_attribute_name(self, obj):
        if obj.attribute:
            return obj.attribute.name
        if ':' in obj.value:
            return obj.value.split(':', 1)[0].strip()
        return 'Custom Attribute'

    def get_value(self, obj):
        if obj.attribute:
            return obj.value
        if ':' in obj.value:
            return obj.value.split(':', 1)[1].strip()
        return obj.value

class AlternativeCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    full_path = serializers.CharField(source='category.full_path', read_only=True)
    
    class Meta:
        model = AlternativeCategory
        fields = ['id', 'category_name', 'full_path', 'confidence', 'rank']

class ClassificationSerializer(serializers.ModelSerializer):
    attributes = ClassificationAttributeSerializer(many=True, read_only=True)
    alternatives = AlternativeCategorySerializer(source='alternative_categories', many=True, read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_description = serializers.CharField(source='product.description', read_only=True)
    product_brand = serializers.CharField(source='product.brand', read_only=True)
    product_image = serializers.SerializerMethodField()
    predicted_category = serializers.CharField(source='predicted_category.name', read_only=True)
    predicted_category_id = serializers.IntegerField(source='predicted_category.id', read_only=True)

    class Meta:
        model = Classification
        fields = [
            'id', 'product', 'product_name', 'product_description', 'product_brand', 'product_image', 
            'predicted_category', 'predicted_category_id', 'confidence', 'status', 
            'requires_manual_review', 'failure_reason', 'attributes', 'alternatives', 'created_at'
        ]
        
    def get_product_image(self, obj):
        if hasattr(obj.product, 'image_urls') and obj.product.image_urls and len(obj.product.image_urls) > 0:
            return obj.product.image_urls[0]
        return None

from taxonomy.models import TaxonomyCategory

class ClassificationUpdateSerializer(serializers.ModelSerializer):
    predicted_category = serializers.PrimaryKeyRelatedField(
        queryset=TaxonomyCategory.objects.all(),
        required=False,
        allow_null=True
    )
    attributes = serializers.JSONField(required=False, write_only=True)

    class Meta:
        model = Classification
        fields = ['predicted_category', 'requires_manual_review', 'status', 'attributes']
        
    def update(self, instance, validated_data):
        attributes_data = validated_data.pop('attributes', None)
        instance = super().update(instance, validated_data)
        
        if attributes_data is not None:
            instance.attributes.all().delete()
            from taxonomy.models import TaxonomyAttribute
            for key, val in attributes_data.items():
                tax_attr = TaxonomyAttribute.objects.filter(name__iexact=key).first()
                if tax_attr:
                    ClassificationAttribute.objects.create(
                        classification=instance,
                        attribute=tax_attr,
                        value=val,
                        confidence=1.0
                    )
                else:
                    ClassificationAttribute.objects.create(
                        classification=instance,
                        attribute=None,
                        value=f"{key}: {val}",
                        confidence=1.0
                    )
        return instance
