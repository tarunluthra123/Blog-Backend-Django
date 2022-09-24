from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.pagination import PageNumberPagination

from api.models import User, Article, ArticleTag
from api.serializers import ArticleSerializer, UserSerializer, ProfileSerializer
from utils.codec import Codec
from utils.jwt import generate_token
from api.permissions import IsAuthenticated


class PingPongView(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self, request):
        return Response({"message": "pingpong"})


class CreateUserView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class ProfileListView(ListAPIView):
    queryset = User.objects.all()
    serializer_class = ProfileSerializer


class ProfileRetrieveView(RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = ProfileSerializer
    lookup_field = "username"


class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        user = User.objects.filter(username=username).first()

        if user and Codec.compare(password, user.password):
            # Check if the user password matches with the given password in the request
            # Generate an auth token and return it.
            payload = {
                "id": user.id,
                "username": user.username,
            }
            token = generate_token(payload)

            serializer = UserSerializer(user)

            return Response({"token": token, **serializer.data})

        return Response({"message": "Invalid credentials"}, status=401)


class ArticlePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "size"


class ArticleCreateListView(ListCreateAPIView):
    serializer_class = ArticleSerializer
    pagination_class = ArticlePagination

    def get_queryset(self):
        query_params = self.request.query_params

        author = query_params.get("author")
        tag = query_params.get("tag")

        if author:
            return Article.objects.filter(author__username=author)

        if tag:
            return Article.objects.filter(tags__name=tag)

        return Article.objects.all()

    def post(self, request, *args, **kwargs):
        data = request.data
        author = request.user
        tags = data.pop("tags")

        article = Article.objects.create(author=author, **data)

        tag_objects = []
        for tag in tags:
            t = ArticleTag.objects.get_or_create(name=tag)[0]
            tag_objects.append(t)

        article.tags.set(tag_objects)

        serializer = ArticleSerializer(article)

        return Response(serializer.data, status=201)


class ArticleRetrieveUpdate(RetrieveUpdateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    lookup_field = "slug"

    def patch(self, request, *args, **kwargs):
        user = request.user
        article = self.get_object()

        if user == article.author:
            return super().patch(request, *args, **kwargs)

        return Response({"message": "You are not authorized to edit this article"}, status=401)
