from rest_framework import serializers


class TextInputSerializer(serializers.Serializer):
    text = serializers.CharField()
    labels = serializers.ListField(
        child=serializers.CharField()
    )


class MaskPIIInputSerializer(serializers.Serializer):
    text = serializers.CharField()
    labels = serializers.ListField(
        child=serializers.CharField()
    )
