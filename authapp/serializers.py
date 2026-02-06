from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Bookmark


class SignupSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=4)

    class Meta:
        model = User
        fields = ["username", "password"]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("이미 존재하는 아이디입니다.")
        return value

    def create(self, validated_data):
        user = User(username=validated_data["username"])
        user.set_password(validated_data["password"])
        user.save()
        return user


class BookmarkSerializer(serializers.ModelSerializer):
    kakao_id = serializers.CharField(source="place.kakao_id", read_only=True)
    name = serializers.CharField(source="place.name", read_only=True)

    lat = serializers.FloatField(source="place.lat", read_only=True)
    lng = serializers.FloatField(source="place.lng", read_only=True)
    class Meta:
        model = Bookmark
        fields = ["id", "kakao_id", "name", "memo","lat","lng", "created_at"]
        read_only_fields = ["id", "created_at", "kakao_id", "name","lat","lng"]


# Swagger / POST 입력칸용
class BookmarkCreateSerializer(serializers.Serializer):
    kakao_id = serializers.CharField(max_length=32)  # Place.kakao_id max_length=32에 맞춤
