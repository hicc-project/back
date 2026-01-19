# authapp/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import (
    SignupSerializer,
    BookmarkSerializer,
    BookmarkCreateSerializer,
)
from .models import Bookmark


@extend_schema(
    request=SignupSerializer,
    responses={
        201: OpenApiResponse(description="회원가입 성공"),
        400: OpenApiResponse(description="요청 오류(중복 아이디/필드 누락 등)"),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "회원가입 성공"}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    methods=["GET"],
    responses={200: BookmarkSerializer(many=True)},
)
@extend_schema(
    methods=["POST"],
    request=BookmarkCreateSerializer,
    responses={
        201: OpenApiResponse(description="즐겨찾기 추가 성공"),
        200: OpenApiResponse(description="이미 즐겨찾기에 있음"),
        400: OpenApiResponse(description="cafe_name 누락"),
        401: OpenApiResponse(description="인증 필요"),
    },
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bookmarks(request):
    if request.method == "GET":
        qs = Bookmark.objects.filter(user=request.user)
        return Response(BookmarkSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    cafe_name = request.data.get("cafe_name")
    if not cafe_name:
        return Response({"detail": "cafe_name이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

    obj, created = Bookmark.objects.get_or_create(user=request.user, cafe_name=cafe_name)
    if not created:
        return Response({"message": "이미 즐겨찾기에 있습니다."}, status=status.HTTP_200_OK)

    return Response(
        {"message": "즐겨찾기에 추가되었습니다.", "bookmark": BookmarkSerializer(obj).data},
        status=status.HTTP_201_CREATED
    )


@extend_schema(
    methods=["DELETE"],
    responses={
        200: OpenApiResponse(description="삭제 성공"),
        404: OpenApiResponse(description="해당 즐겨찾기 없음"),
        401: OpenApiResponse(description="인증 필요"),
    },
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def bookmark_delete(request, bookmark_id: int):
    deleted, _ = Bookmark.objects.filter(id=bookmark_id, user=request.user).delete()
    if deleted == 0:
        return Response({"detail": "해당 즐겨찾기를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
    return Response({"message": "즐겨찾기가 삭제되었습니다."}, status=status.HTTP_200_OK)


class LoginView(TokenObtainPairView):
    """
    Swagger 입력칸(username/password)은 TokenObtainPairView 기본 스키마로도 뜨는 편이지만,
    응답을 커스텀했으니 실패 응답을 한글로 통일한 로직은 유지.
    """
    def post(self, request, *args, **kwargs):
        resp = super().post(request, *args, **kwargs)

        if resp.status_code == status.HTTP_200_OK:
            data = resp.data
            return Response(
                {
                    "message": "로그인 되었습니다.",
                    "access": data.get("access"),
                    "refresh": data.get("refresh"),
                },
                status=status.HTTP_200_OK
            )

        if resp.status_code == status.HTTP_401_UNAUTHORIZED:
            return Response(
                {"detail": "아이디 또는 비밀번호가 올바르지 않습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if resp.status_code == status.HTTP_400_BAD_REQUEST:
            return Response(
                {"detail": "요청이 올바르지 않습니다.", "errors": resp.data},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(resp.data, status=resp.status_code)
