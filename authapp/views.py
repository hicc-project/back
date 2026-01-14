# authapp/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .serializers import SignupSerializer, BookmarkSerializer
from .models import Bookmark


def _flatten_serializer_errors(errors: dict) -> str:
    """
    serializer.errors (dict)를 사람이 읽기 좋은 한 줄 메시지로 변환
    예: {"username": ["이미 존재하는 아이디입니다."]} -> "이미 존재하는 아이디입니다."
    """
    if not isinstance(errors, dict):
        return "요청이 올바르지 않습니다."

    # 가장 흔한 케이스: 특정 필드 에러가 list로 들어옴
    for field, msgs in errors.items():
        if isinstance(msgs, list) and len(msgs) > 0:
            return str(msgs[0])
        if isinstance(msgs, str):
            return msgs

    return "요청이 올바르지 않습니다."


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response({"message": "회원가입 성공"}, status=status.HTTP_201_CREATED)

    # 중복 아이디 포함 모든 validation 에러를 message로 통일
    msg = _flatten_serializer_errors(serializer.errors)
    return Response(
        {"message": msg, "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bookmarks(request):
    if request.method == "GET":
        qs = Bookmark.objects.filter(user=request.user)
        return Response(BookmarkSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    # POST: 즐겨찾기 추가
    cafe_name = request.data.get("cafe_name")
    if not cafe_name:
        return Response({"message": "cafe_name이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

    obj, created = Bookmark.objects.get_or_create(user=request.user, cafe_name=cafe_name)
    if not created:
        return Response({"message": "이미 즐겨찾기에 있습니다."}, status=status.HTTP_200_OK)

    return Response(
        {"message": "즐겨찾기에 추가되었습니다.", "bookmark": BookmarkSerializer(obj).data},
        status=status.HTTP_201_CREATED
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def bookmark_delete(request, bookmark_id: int):
    deleted, _ = Bookmark.objects.filter(id=bookmark_id, user=request.user).delete()
    if deleted == 0:
        return Response({"message": "해당 즐겨찾기를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

    return Response({"message": "즐겨찾기가 삭제되었습니다."}, status=status.HTTP_200_OK)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        # 입력 누락도 알려주기
        if not username:
            return Response({"message": "username이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"message": "password가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            resp = super().post(request, *args, **kwargs)
            data = resp.data
            return Response(
                {
                    "message": "로그인 되었습니다.",
                    "access": data.get("access"),
                    "refresh": data.get("refresh"),
                },
                status=status.HTTP_200_OK
            )

        # 아이디/비번 틀리면 한국어 메시지로 통일
        except (InvalidToken, TokenError):
            return Response(
                {"message": "아이디 또는 비밀번호가 올바르지 않습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )
