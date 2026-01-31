# authapp/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import signup, bookmarks, bookmark_delete, bookmark_memo_update, LoginView

urlpatterns = [
    path("signup/", signup),

    #로그인(=token을 감싼 커스텀 응답)
    path("login/", LoginView.as_view()),

    # 토큰 발급, 갱신
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # 즐겨찾기
    path("bookmarks/", bookmarks),  # GET, POST
    path("bookmarks/<int:bookmark_id>/", bookmark_delete),  # DELETE

    #메모
    path("bookmarks/<int:bookmark_id>/memo/", bookmark_memo_update),
]
