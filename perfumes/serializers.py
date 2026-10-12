from rest_framework import serializers

class CartItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
    quantity = serializers.IntegerField(min_value=1, max_value=2147483647)

class PurchaseSerializer(serializers.Serializer):
    email = serializers.EmailField()
    cart = CartItemSerializer(many=True, allow_empty=False, max_length=100)

    def validate_cart(self, items):
        ids = [item['id'] for item in items]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError('Each perfume must appear only once in the cart.')
        return items


class StockRequestSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
