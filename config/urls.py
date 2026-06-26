from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('auth/', include('django.contrib.auth.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('transactions/', include('apps.transactions.urls')),
    path('cards/', include('apps.cards.urls')),
    path('categories/', include('apps.categories.urls')),
    path('budgets/', include('apps.budgets.urls')),
    path('reports/', include('apps.reports.urls')),
    path('investments/', include('apps.investments.urls')),
    path('integrations/pluggy/', include('apps.integrations.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
