# authapp/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Bookmark

class SignupSerializer(serializers.ModelSerializer):
    # username을 "아이디"로 쓰기
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
    class Meta:
        model = Bookmark
        fields = ["id", "cafe_name", "created_at"]
        read_only_fields = ["id", "created_at"]
        
#Swagger/POST 입력칸용
class BookmarkCreateSerializer(serializers.Serializer):
    cafe_name = serializers.CharField(max_length=255)
