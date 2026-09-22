from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import UsuarioViewSet, EquipamientoViewSet, PerfilGenericoViewSet, IPViewSet, AnexoViewSet, PCGenericoViewSet, ServidorViewSet, DepartamentoViewSet, SubAreaViewSet
from core.auth_views import LoginView, RefreshCookieView, LogoutView, MeView
from core.security_views import RevealSecretView

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'equipos', EquipamientoViewSet, basename='equipo')
router.register(r'perfiles-genericos', PerfilGenericoViewSet, basename='perfilgenerico')
router.register(r'anexos', AnexoViewSet, basename='anexo')
router.register(r'ips', IPViewSet, basename='ip')
router.register(r'pcs-genericos', PCGenericoViewSet, basename='pc')
router.register(r'servidores', ServidorViewSet, basename='servidor')
router.register(r'departamentos', DepartamentoViewSet, basename='departamento')
router.register(r'subareas', SubAreaViewSet, basename='subarea')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/refresh/', RefreshCookieView.as_view(), name='refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/me/', MeView.as_view(), name='me'),
    path('api/secrets/reveal/', RevealSecretView.as_view(), name='reveal-secret'),
    path('api/', include(router.urls)),
]
