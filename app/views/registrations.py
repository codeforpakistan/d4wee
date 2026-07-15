from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.conf import settings
from ..models import (
    Student,
    Cohort,
    Registration,
)


@login_required
@staff_member_required
def registration_list(request):
    """
    Staff view to see and manage all registrations
    """
    # Get filter from query params
    status_filter = request.GET.get("status", "PENDING")
    page_number = request.GET.get("page", 1)
    search_query = request.GET.get("q", "").strip()

    # Show all registrations
    registrations = Registration.objects.select_related(
        "student", "cohort", "approved_by"
    )

    if status_filter and status_filter != "ALL":
        registrations = registrations.filter(status=status_filter)

    # Apply search filter if query provided
    if search_query:
        registrations = registrations.filter(
            Q(student__full_name__icontains=search_query) | Q(student__email__icontains=search_query)
        )

    registrations = registrations.order_by("student__full_name")

    # Paginate results (1500 per page)
    paginator = Paginator(registrations, settings.PER_PAGE)
    page_obj = paginator.get_page(page_number)

    context = {
        "registrations": page_obj,
        "page_obj": page_obj,
        "status_filter": status_filter,
        "search_query": search_query,
    }

    return render(request, "app/registration_list.html", context)


@login_required
@staff_member_required
def registration_detail(request, status):
    """
    Staff view to see and manage all registrations
    """
    # Get filter from query params
    page_number = request.GET.get("page", 1)
    search_query = request.GET.get("q", "").strip()

    # Show all registrations
    registrations = Registration.objects.select_related(
        "student", "cohort", "approved_by"
    )

    if status and status != "all":
        registrations = registrations.filter(status=status.upper())

    # Apply search filter if query provided
    if search_query:
        registrations = registrations.filter(
            Q(student__full_name__icontains=search_query) | Q(student__email__icontains=search_query)
        )

    registrations = registrations.order_by("student__full_name")

    # Paginate results (1500 per page)
    paginator = Paginator(registrations, settings.PER_PAGE)
    page_obj = paginator.get_page(page_number)

    context = {
        "registrations": page_obj,
        "page_obj": page_obj,
        "status_filter": status.upper(),
        "search_query": search_query,
    }

    return render(request, "app/registration_list.html", context)


@login_required
def registration_create(request, cohort_id):
    """Handle cohort registration request - for non-staff users"""
    # Staff users should use admin interface
    if request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Staff members should use the admin interface.")
        return redirect("cohort_list")

    cohort = get_object_or_404(Cohort, id=cohort_id)

    # Get or create student profile when registering for cohort
    try:
        # First try to get by user
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        # Try to find existing student by email (from Google Classroom sync)
        try:
            student = Student.objects.get(email=request.user.email)
            # Link this existing student to the user account
            student.user = request.user
            student.save()
        except Student.DoesNotExist:
            # Create new student profile
            student = Student.objects.create(
                user=request.user,
                email=request.user.email,
                full_name=request.user.get_full_name() or request.user.username,
                google_id=f"local_{request.user.id}",
            )

    # Check if cohort is open for registration
    if not cohort.is_open_for_registration:
        messages.error(
            request, f"{cohort.name} is not currently open for registration."
        )
        return redirect("home")

    # Check if cohort can accept registrations
    if not cohort.can_accept_registrations:
        messages.error(request, f"{cohort.name} has reached its maximum capacity.")
        return redirect("home")

    # Check if already registered
    existing = Registration.objects.filter(student=student, cohort=cohort).first()
    if existing:
        messages.warning(
            request,
            f"You already have a {existing.status.lower()} registration for {cohort.name}.",
        )
        return redirect("home")

    # Create registration request
    Registration.objects.create(
        student=student,
        cohort=cohort,
        status="PENDING",
        notes=f"Self-registration via web interface by {request.user.username}",
    )

    messages.success(
        request,
        f"Your registration request for {cohort.name} has been submitted! "
        f"An administrator will review it shortly.",
    )

    return redirect("home")


@login_required
@staff_member_required
@require_POST
def approve_registration(request, registration_id):
    """
    Approve a registration (POST only)
    """
    registration = get_object_or_404(Registration, id=registration_id)

    if registration.status != "PENDING":
        messages.warning(
            request, f"Registration is already {registration.status.lower()}."
        )
    else:
        registration.approve(request.user)
        messages.success(
            request, f"Approved registration for {registration.student.full_name}."
        )

    # Redirect back to registrations list
    return redirect("registration_list")


@login_required
@staff_member_required
@require_POST
def reject_registration(request, registration_id):
    """
    Reject a registration (POST only)
    """
    registration = get_object_or_404(Registration, id=registration_id)

    if registration.status != "PENDING":
        messages.warning(
            request, f"Registration is already {registration.status.lower()}."
        )
    else:
        reason = request.POST.get("reason", "")
        registration.reject(request.user, reason=reason)
        messages.success(
            request, f"Rejected registration for {registration.student.full_name}."
        )

    # Redirect back to registrations list
    return redirect("registration_list")
