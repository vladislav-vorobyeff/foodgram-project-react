from api.views import (DownloadShoppingCartViewSet, FavoriteViewSet,
                       IngredientViewSet, RecipeViewSet, ShoppingCartViewSet,
                       SubscriptionsViewSet, TagViewSet, UserViewSet)
from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register('users', UserViewSet, basename='users')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('tags', TagViewSet, basename='tags')
router.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path(
        'users/subscriptions/',
        SubscriptionsViewSet.as_view({'get': 'list'}),
        name='subscriptions'
    ),
    re_path(
        r'recipes/(?P<recipe_id>\d+)/favorite/',
        FavoriteViewSet.as_view({'post': 'create', 'delete': 'delete'}),
        name='favorites'
    ),
    re_path(
        r'recipes/(?P<recipe_id>\d+)/shopping_cart/',
        ShoppingCartViewSet.as_view({'post': 'create', 'delete': 'delete'}),
        name='shopping_cart'
    ),
    path(
        'recipes/download_shopping_cart/',
        DownloadShoppingCartViewSet.as_view(),
        name='download'
    ),
    re_path(
        r'users/(?P<author_id>\d+)/subscribe/',
        SubscriptionsViewSet.as_view({'post': 'create', 'delete': 'delete'}),
        name='subscribe'
    ),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
]
