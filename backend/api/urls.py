from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .ingredients.views import IngredientViewSet
from .recipes.views import RecipeViewSet, DownloadShoppingCartViewSet
from .tags.views import TagViewSet
from .users.views import CustomUserViewSet

app_name = 'api'

router_v1 = DefaultRouter()

router_v1.register('ingredients', IngredientViewSet, basename='ingredients')
router_v1.register('tags', TagViewSet, basename='tags')
router_v1.register('recipes', RecipeViewSet, basename='recipes')
router_v1.register('users', CustomUserViewSet, basename='users')

urlpatterns = [
    path('', include(router_v1.urls)),
    path('auth/', include('djoser.urls.authtoken')),
    path(
        'recipes/download_shopping_cart/',
        DownloadShoppingCartViewSet.as_view(),
        name='download'
    ),
]
