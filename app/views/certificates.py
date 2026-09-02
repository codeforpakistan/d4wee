import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import render

from app.models import Certificate, Cohort

logger = logging.getLogger(__name__)

@login_required
@staff_member_required
def certificate_list(request):
    """Display student attendance records - requires staff access"""
    certificates = Certificate.objects.all().prefetch_related('enrollment__registration__student')

    search_query = request.GET.get("q", "").strip()
    cohort_query = request.GET.get("cohort", "").strip()

    if search_query:
        certificates = certificates.filter(
            Q(enrollment__registration__student__full_name__icontains=search_query) | Q(enrollment__registration__student__email__icontains=search_query)
        )

    if cohort_query:
        cohort_query = int(cohort_query)
        certificates = certificates.filter(enrollment__registration__cohort=cohort_query)
    

    # Paginate students (20 per page)
    paginator = Paginator(certificates, settings.PER_PAGE)
    page = request.GET.get("page", 1)

    try:
        certs_page = paginator.page(page)
    except PageNotAnInteger:
        certs_page = paginator.page(1)
    except EmptyPage:
        certs_page = paginator.page(paginator.num_pages)

    context = {
        "certificates": certs_page,
        "cohorts": Cohort.objects.all().order_by('id'),
        "search_query": search_query,
        "cohort_query": cohort_query,

    }
    return render(request, "app/certificate_list.html", context)
