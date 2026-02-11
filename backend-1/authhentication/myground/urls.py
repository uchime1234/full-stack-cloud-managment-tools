from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'aws-accounts', views.AWSAccountViewSet, basename='awsaccount')
router.register(r'resources', views.ResourceViewSet, basename='resource')  # Add this


urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    # Token-based MFA endpoints (for post-registration)
    path('mfa/setup-token/', views.mfa_setup_init_token, name='mfa_setup_token'),
    path('mfa/enable-token/', views.mfa_enable_token, name='mfa_enable_token'),
    # Authenticated MFA endpoints (for logged-in users)
    path('mfa/setup/', views.mfa_setup_init, name='mfa_setup'),
    path('mfa/enable/', views.mfa_enable, name='mfa_enable'),
    path('mfa/verify/', views.mfa_verify, name='mfa_verify'),
    path('mfa/disable/', views.mfa_disable, name='mfa_disable'),
    path('mfa/status/', views.mfa_status, name='mfa_status'),
    path('mfa/regenerate-backup/', views.regenerate_backup_codes, name='regenerate_backup'),
    path("aws/info/", views.aws_platform_info, name="aws-platform-info"),  # Removed api/ prefix
    path("aws/generate-external-id/", views.generate_external_id, name='generate_external_id'),
    path("aws/connect-account/", views.connect_aws_account, name='connect_aws_account'),
    path('check-auth/', views.check_auth, name='check_auth'),
    path('aws-accounts/<int:account_id>/fetch-costs/', views.FetchAWSCostsView.as_view(), name='fetch-costs'),
    path('aws-accounts/<int:account_id>/analytics/', views.AWSAccountViewSet.as_view({'get': 'analytics'}), name='cost-analytics'),
    path('aws-accounts/<int:account_id>/sync/', views.AWSAccountViewSet.as_view({'post': 'sync'}), name='sync-account'),
    path('debug-monthly-change/<int:account_id>/', views.debug_monthly_change, name='debug_monthly_change'),
    path('test-resources/<int:account_id>/', views.test_resources, name='test_resources'), 
    path('resources/<int:pk>/resource_summary/', views.ResourceViewSet.as_view({'get': 'resource_summary'}), name='resource-summary'),
    path('resources/<int:pk>/clear_cache/', views.ResourceViewSet.as_view({'post': 'clear_cache'}), name='clear-cache'),
    path('resources/<int:pk>/paid-resources/',  views.ResourceViewSet.as_view({'get': 'paid_resources'}), name='paid-resources'),
    path('resources/<int:pk>/cost-analysis/', views.ResourceViewSet.as_view({'get': 'cost_analysis'}), name='cost-analysis'),
    path('api/aws/accounts/<int:account_id>/low-level-services/',  views.low_level_services,  name='low-level-services'),
    path('api/aws/accounts/<int:account_id>/low-level-services/<str:category>/', views.low_level_services_by_category,  name='low-level-services-category'),
    path('api/aws/accounts/<int:account_id>/low-level-cost-summary/', views.low_level_cost_summary,  name='low-level-cost-summary'),
    path('api/aws/accounts/<int:account_id>/low-level-services/export/<str:format>/', views.export_low_level_services,  name='low-level-services-export'),
 
]