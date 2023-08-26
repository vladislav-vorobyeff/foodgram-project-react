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
            subscriptions = Subscriptions.objects.filter(
                user=self.request.user
            )
            return [subscription.following for subscription in subscriptions]
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
        if user.is_authenticated:
            if not Subscriptions.objects.filter(
                    user=user,
                    following=following).exists():
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
            return Response(
                'Подписка уже оформлена',
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            'Необходима авторизация',
            status=status.HTTP_401_UNAUTHORIZED
        )

    @subscribe.mapping.delete
    def unsubscribe(self, request, id):
        following = get_object_or_404(User, id=id)
        user = request.user
        if user.is_authenticated:
            subscription = Subscriptions.objects.filter(
                user=user, following=following)
            if subscription.exists():
                subscription.delete()
                return Response('Подписка удалена')
            return Response(
                'Нельзя удалить несуществующую'
                ' подписку',
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            'Необходима авторизация',
            status=status.HTTP_401_UNAUTHORIZED
        )
