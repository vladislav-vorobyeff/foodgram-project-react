from api.views import (DownloadShoppingCartViewSet, IngredientViewSet,
                       RecipeViewSet, TagViewSet, UserViewSet)
from django.urls import include, path
from rest_framework.routers import DefaultRouter

router_v1 = DefaultRouter()

router_v1.register('users', UserViewSet, basename='users')
router_v1.register('recipes', RecipeViewSet, basename='recipes')
router_v1.register('ingredients', IngredientViewSet, basename='ingredients')
router_v1.register('tags', TagViewSet, basename='tags')

urlpatterns = [
    path(
        'recipes/download_shopping_cart/',
        DownloadShoppingCartViewSet.as_view(),
        name='download'
    ),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router_v1.urls)),
]
