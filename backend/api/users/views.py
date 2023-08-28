from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import Subscriptions
from .serializers import CustomUserRecSerializer

User = get_user_model()


class CustomUserViewSet(UserViewSet):

    def get_queryset(self):
        if self.action == 'subscriptions':
            return self.request.user.following.all()
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'subscriptions':
            return CustomUserRecSerializer
        return super().get_serializer_class()

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[IsAuthenticated],
    )
    def subscriptions(self, request):
        return self.list(request)

    @action(
        detail=True,
        methods=['POST'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id):
        following = get_object_or_404(User, id=id)
        user = request.user
        if request.user == following:
            return Response('Нельзя оформить подписку на себя')
        if Subscriptions.objects.filter(
                user=user,
                following=following).exists():
            return Response(
                'Подписка уже оформлена',
                status=status.HTTP_400_BAD_REQUEST
            )
        Subscriptions.objects.create(
            user=user,
            following=following
        )
        serializer = CustomUserRecSerializer(
            following,
            context={'request': request}
        )
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def unsubscribe(self, request, id):
        following = get_object_or_404(User, id=id)
        user = request.user
        subscription = Subscriptions.objects.filter(
            user=user, following=following)
        if not subscription.exists():
            return Response(
                'Нельзя удалить несуществующую'
                ' подписку',
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.delete()
        return Response('Подписка удалена')
