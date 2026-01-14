# authapp/views.py
from rest_framework_simplejwt.views import TokenObtainPairView

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

    # serializer에서 잡힌 에러(아이디 중복 등)를 그대로 내려줌
    # 예) {"username": ["이미 존재하는 아이디입니다."]}
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bookmarks(request):
    if request.method == "GET":
        qs = Bookmark.objects.filter(user=request.user)
        return Response(BookmarkSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    # POST: 즐겨찾기 추가
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


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def bookmark_delete(request, bookmark_id: int):
    deleted, _ = Bookmark.objects.filter(id=bookmark_id, user=request.user).delete()
    if deleted == 0:
        return Response({"detail": "해당 즐겨찾기를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

    return Response({"message": "즐겨찾기가 삭제되었습니다."}, status=status.HTTP_200_OK)


class LoginView(TokenObtainPairView):
    """
    - 성공(200): message + access/refresh
    - 실패(401): 한글 메시지로 통일
    - 요청 누락/형식 오류(400): 한글 메시지로 통일 + 어떤 필드가 문제인지 함께 내려줌
    """

    def post(self, request, *args, **kwargs):
        resp = super().post(request, *args, **kwargs)

        # 성공
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

        # 실패(보통 아이디/비번 틀림, 비활성 계정 등)
        if resp.status_code == status.HTTP_401_UNAUTHORIZED:
            return Response(
                {"detail": "아이디 또는 비밀번호가 올바르지 않습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 그 외(대부분 400: username/password 누락 등)
        if resp.status_code == status.HTTP_400_BAD_REQUEST:
            # 원본 에러도 같이 주면 프론트에서 디버깅/표시하기 좋음
            return Response(
                {
                    "detail": "요청이 올바르지 않습니다.",
                    "errors": resp.data,  # 예: {"username": ["This field is required."]}
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 기타 상태코드도 안전하게 전달
        return Response(resp.data, status=resp.status_code)
