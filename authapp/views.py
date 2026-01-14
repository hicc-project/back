# authapp/views.py
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .serializers import SignupSerializer, BookmarkSerializer
from .models import Bookmark

@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "회원가입 성공"}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bookmarks(request):
    if request.method == "GET":
        qs = Bookmark.objects.filter(user=request.user)
        return Response(BookmarkSerializer(qs, many=True).data)

    # POST: 즐겨찾기 추가
    cafe_name = request.data.get("cafe_name")
    if not cafe_name:
        return Response({"detail": "cafe_name이 필요합니다."}, status=400)

    obj, created = Bookmark.objects.get_or_create(user=request.user, cafe_name=cafe_name)
    if not created:
        return Response({"message": "이미 즐겨찾기에 있습니다."}, status=200)

    return Response(
        {"message": "즐겨찾기에 추가되었습니다.", "bookmark": BookmarkSerializer(obj).data},
        status=201
    )

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def bookmark_delete(request, bookmark_id: int):
    # 본인 것만 삭제
    deleted, _ = Bookmark.objects.filter(id=bookmark_id, user=request.user).delete()
    if deleted == 0:
        return Response({"detail": "해당 즐겨찾기를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
    return Response({"message": "즐겨찾기가 삭제되었습니다."}, status=status.HTTP_200_OK)

