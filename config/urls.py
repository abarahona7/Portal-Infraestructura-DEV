from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import UsuarioViewSet, EquipamientoViewSet, PerfilGenericoViewSet, IPViewSet, AnexoViewSet, PCGenericoViewSet, ServidorViewSet, DepartamentoViewSet, SubAreaViewSet, ReferenceDataView
from core.auth_views import ActivityView, CsrfTokenView, LoginView, RefreshCookieView, LogoutView, MeView
from core.security_views import RevealSecretView
from core.asset_api import ActaEntregaViewSet, MovimientoActivoViewSet
from core.asset_qr import AssetQrImageView, AssetQrView
from core.asset_dashboard import AssetDashboardView, AssetInactiveCustodianView, AssetMissingIdentifierView, AssetTechnicalPendingView, AssetUnassignedView, AssetWarrantyView

router = DefaultRouter()
router.register(r'movimientos', MovimientoActivoViewSet, basename='movimiento')
router.register(r'actas', ActaEntregaViewSet, basename='acta')
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
    path('api/auth/csrf/', CsrfTokenView.as_view(), name='csrf-token'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/refresh/', RefreshCookieView.as_view(), name='refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/activity/', ActivityView.as_view(), name='activity'),
    path('api/auth/me/', MeView.as_view(), name='me'),
    path('api/secrets/reveal/', RevealSecretView.as_view(), name='reveal-secret'),
    path('api/reference-data/', ReferenceDataView.as_view(), name='reference-data'),
    path('api/activos/resumen/', AssetDashboardView.as_view(), name='activos-resumen'),
    path('api/activos/identificadores-faltantes/', AssetMissingIdentifierView.as_view(), name='activos-identificadores-faltantes'),
    path('api/activos/pendientes-tecnicos/', AssetTechnicalPendingView.as_view(), name='activos-pendientes-tecnicos'),
    path('api/activos/custodios-no-activos/', AssetInactiveCustodianView.as_view(), name='activos-custodios-no-activos'),
    path('api/activos/sin-custodio/', AssetUnassignedView.as_view(), name='activos-sin-custodio'),
    path('api/activos/garantias/', AssetWarrantyView.as_view(), name='activos-garantias'),
    path('api/activos/qr/<uuid:token>/', AssetQrView.as_view(), name='activo-qr'),
    path('api/activos/qr/<uuid:token>/imagen/', AssetQrImageView.as_view(), name='activo-qr-imagen'),
    path('api/', include(router.urls)),
]
