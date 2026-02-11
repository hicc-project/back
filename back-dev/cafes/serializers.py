from rest_framework import serializers
from .models import Place

class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ["kakao_id", "name", "address", "lat", "lng", "place_url"]
