"""
URL configuration for admin_panel project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Materials
    path('materials/', views.MaterialListView.as_view(), name='material-list'),
    path('materials/create/', views.MaterialCreateView.as_view(), name='material-create'),
    path('materials/<int:pk>/edit/', views.MaterialUpdateView.as_view(), name='material-edit'),
    path('materials/<int:pk>/delete/', views.MaterialDeleteView.as_view(), name='material-delete'),
    
    # Publications
    path('publications/', views.PublicationListView.as_view(), name='publication-list'),
    path('publications/create/', views.PublicationCreateView.as_view(), name='publication-create'),
    path('publications/<int:pk>/edit/', views.PublicationUpdateView.as_view(), name='publication-edit'),
    path('publications/<int:pk>/delete/', views.PublicationDeleteView.as_view(), name='publication-delete'),
    
    # Campaigns
    path('campaigns/', views.CampaignListView.as_view(), name='campaign-list'),
    path('campaigns/create/', views.CampaignCreateView.as_view(), name='campaign-create'),
    path('campaigns/<int:pk>/edit/', views.CampaignUpdateView.as_view(), name='campaign-edit'),
    path('campaigns/<int:pk>/delete/', views.CampaignDeleteView.as_view(), name='campaign-delete'),
    path('campaigns/<int:campaign_id>/metrics/', views.update_campaign_metrics, name='campaign-metrics'),
    
    # Requests from posts
    path('requests/', views.RequestFromPostListView.as_view(), name='request-list'),
    path('requests/<int:pk>/', views.RequestFromPostDetailView.as_view(), name='request-detail'),
    path('api/toggle-ai-assistant/', views.toggle_ai_assistant, name='toggle_ai_assistant'),
]
