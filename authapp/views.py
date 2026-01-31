from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from cafes.models import Place
from .serializers import SignupSerializer, BookmarkSerializer, BookmarkCreateSerializer
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
    request=BookmarkCreateSerializer,  # ⚠️ 이 serializer는 kakao_id만 받도록 수정 권장
    responses={
        201: OpenApiResponse(description="즐겨찾기 추가 성공"),
        200: OpenApiResponse(description="이미 즐겨찾기에 있음"),
        400: OpenApiResponse(description="kakao_id 누락"),
        401: OpenApiResponse(description="인증 필요"),
        404: OpenApiResponse(description="해당 kakao_id의 Place 없음"),
    },
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bookmarks(request):
    # ✅ 즐겨찾기 목록 조회
    if request.method == "GET":
        qs = Bookmark.objects.filter(user=request.user).select_related("place")
        return Response(BookmarkSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    # ✅ 즐겨찾기 추가 (memo는 받지 않음)
    kakao_id = request.data.get("kakao_id")

    if not kakao_id:
        return Response({"detail": "kakao_id가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        place = Place.objects.get(pk=kakao_id)
    except Place.DoesNotExist:
        return Response({"detail": "해당 kakao_id의 카페를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

    obj, created = Bookmark.objects.get_or_create(
        user=request.user,
        place=place,
        # memo는 모델 default=""로 자동 처리됨
    )

    if not created:
        return Response({"message": "이미 즐겨찾기에 있습니다."}, status=status.HTTP_200_OK)

    return Response(
        {"message": "즐겨찾기에 추가되었습니다.", "bookmark": BookmarkSerializer(obj).data},
        status=status.HTTP_201_CREATED
    )


@extend_schema(
    methods=["PATCH"],
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "memo": {"type": "string", "example": "내 메모"}
            },
            "required": ["memo"],
        }
    },
    responses={
        200: OpenApiResponse(description="메모 저장 성공"),
        400: OpenApiResponse(description="memo 누락"),
        404: OpenApiResponse(description="해당 즐겨찾기 없음"),
        401: OpenApiResponse(description="인증 필요"),
    },
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def bookmark_memo_update(request, bookmark_id: int):
    """
    ✅ 즐겨찾기 메모만 수정하는 엔드포인트
    PATCH /api/auth/bookmarks/{bookmark_id}/memo/
    body: { "memo": "..." }
    """
    # memo를 '없으면 에러'로 할지, '없으면 빈문자 저장'으로 할지 선택 가능
    if "memo" not in request.data:
        return Response({"detail": "memo가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

    memo = request.data.get("memo", "")
    if memo is None:
        memo = ""

    bookmark = Bookmark.objects.filter(id=bookmark_id, user=request.user).first()
    if not bookmark:
        return Response({"detail": "해당 즐겨찾기를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

    bookmark.memo = memo
    bookmark.save(update_fields=["memo"])

    return Response(
        {"message": "메모가 저장되었습니다.", "bookmark": BookmarkSerializer(bookmark).data},
        status=status.HTTP_200_OK
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
