from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count
from django.http import JsonResponse
from .models import Material, Publication, Campaign, RequestFromPost, BotSettings
from .forms import MaterialForm, PublicationForm, CampaignForm
import json
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.conf import settings

class MaterialListView(LoginRequiredMixin, ListView):
    model = Material
    template_name = 'admin_panel/materials/list.html'
    context_object_name = 'materials'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        return queryset

class MaterialCreateView(LoginRequiredMixin, CreateView):
    model = Material
    form_class = MaterialForm
    template_name = 'admin_panel/materials/form.html'
    success_url = reverse_lazy('material-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Material created successfully'))
        return super().form_valid(form)

class MaterialUpdateView(LoginRequiredMixin, UpdateView):
    model = Material
    form_class = MaterialForm
    template_name = 'admin_panel/materials/form.html'
    success_url = reverse_lazy('admin_panel:material-list')

    def form_valid(self, form):
        messages.success(self.request, _('Material updated successfully'))
        return super().form_valid(form)

class MaterialDeleteView(LoginRequiredMixin, DeleteView):
    model = Material
    template_name = 'admin_panel/materials/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:material-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Material deleted successfully'))
        return super().delete(request, *args, **kwargs)

class PublicationListView(LoginRequiredMixin, ListView):
    model = Publication
    template_name = 'admin_panel/publications/list.html'
    context_object_name = 'publications'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['scheduled_count'] = Publication.objects.filter(status='scheduled').count()
        return context

class PublicationCreateView(LoginRequiredMixin, CreateView):
    model = Publication
    form_class = PublicationForm
    template_name = 'admin_panel/publications/form.html'
    success_url = reverse_lazy('publication-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Publication scheduled successfully'))
        return super().form_valid(form)

class PublicationUpdateView(LoginRequiredMixin, UpdateView):
    model = Publication
    form_class = PublicationForm
    template_name = 'admin_panel/publications/form.html'
    success_url = reverse_lazy('admin_panel:publication-list')

    def form_valid(self, form):
        messages.success(self.request, _('Publication updated successfully'))
        return super().form_valid(form)

class PublicationDeleteView(LoginRequiredMixin, DeleteView):
    model = Publication
    template_name = 'admin_panel/publications/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:publication-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Publication deleted successfully'))
        return super().delete(request, *args, **kwargs)

class CampaignListView(LoginRequiredMixin, ListView):
    model = Campaign
    template_name = 'admin_panel/campaigns/list.html'
    context_object_name = 'campaigns'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_budget'] = Campaign.objects.filter(
            status='active'
        ).aggregate(Sum('budget'))['budget__sum'] or 0
        return context

class CampaignCreateView(LoginRequiredMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'admin_panel/campaigns/form.html'
    success_url = reverse_lazy('campaign-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Campaign created successfully'))
        return super().form_valid(form)

class CampaignUpdateView(LoginRequiredMixin, UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'admin_panel/campaigns/form.html'
    success_url = reverse_lazy('admin_panel:campaign-list')

    def form_valid(self, form):
        messages.success(self.request, _('Campaign updated successfully'))
        return super().form_valid(form)

class CampaignDeleteView(LoginRequiredMixin, DeleteView):
    model = Campaign
    template_name = 'admin_panel/campaigns/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:campaign-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Campaign deleted successfully'))
        return super().delete(request, *args, **kwargs)

class RequestFromPostListView(LoginRequiredMixin, ListView):
    model = RequestFromPost
    template_name = 'admin_panel/requests/list.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by('-created_at')

class RequestFromPostDetailView(LoginRequiredMixin, UpdateView):
    model = RequestFromPost
    template_name = 'admin_panel/requests/detail.html'
    fields = ['status', 'assigned_to', 'response']
    success_url = reverse_lazy('admin_panel:request-list')

    def form_valid(self, form):
        messages.success(self.request, _('Request updated successfully'))
        return super().form_valid(form)

def dashboard(request):
    """Analytics dashboard view"""
    if not request.user.is_authenticated:
        return redirect('login')

    # Gather KPI data
    kpi_data = {
        'total_materials': Material.objects.count(),
        'active_campaigns': Campaign.objects.filter(status='active').count(),
        'pending_requests': RequestFromPost.objects.filter(status='new').count(),
        'scheduled_publications': Publication.objects.filter(status='scheduled').count(),
    }

    # Campaign performance
    campaigns = Campaign.objects.filter(status='active').values('name', 'metrics')
    campaign_performance = []
    for campaign in campaigns:
        metrics = campaign['metrics']
        campaign_performance.append({
            'name': campaign['name'],
            'impressions': metrics.get('impressions', 0),
            'clicks': metrics.get('clicks', 0),
            'conversions': metrics.get('conversions', 0),
        })

    # Request statistics
    request_stats = RequestFromPost.objects.values('status').annotate(
        count=Count('id')
    )

    context = {
        'kpi_data': kpi_data,
        'campaign_performance': campaign_performance,
        'request_stats': request_stats,
    }

    return render(request, 'admin_panel/dashboard.html', context)

def update_campaign_metrics(request, campaign_id):
    """AJAX endpoint for updating campaign metrics"""
    if not request.user.is_authenticated or not request.is_ajax():
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        campaign = Campaign.objects.get(id=campaign_id)
        metrics = json.loads(request.body)
        campaign.metrics = metrics
        campaign.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def toggle_ai_assistant(request):
    """Toggle AI assistant state"""
    settings = BotSettings.get_settings()
    settings.ai_assistant_enabled = not settings.ai_assistant_enabled
    settings.save()
    
    return JsonResponse({
        'enabled': settings.ai_assistant_enabled,
        'message': 'AI assistant {} successfully'.format(
            'enabled' if settings.ai_assistant_enabled else 'disabled'
        )
    }) 