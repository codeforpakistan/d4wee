
import datetime
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from app.models import Cohort, Attendance, Student, AttendanceWeekly
from django.contrib import messages


@login_required
@staff_member_required
def attendance_weekly(request):
    """Display student attendance by week - requires staff access"""

    attendance = AttendanceWeekly.objects.all()
    return render(request, "app/attendance.html", {"attendance": attendance})

    from collections import defaultdict

    # Get filter parameters
    selected_cohort = request.GET.get("cohort", None)
    selected_week = request.GET.get("week", None)
    if selected_week:
        selected_week = int(selected_week)

    # Base queryset
    attendance_records = Attendance.objects.all()

    # Apply cohort filter
    if selected_cohort:
        attendance_records = attendance_records.filter(cohort_id=selected_cohort)

    # Group attendance by week
    weeks_data = defaultdict(
        lambda: {
            "week_number": 0,
            "present_count": 0,
            "total_count": 0,
            "start_date": None,
            "end_date": None,
            "unique_students": set(),
            "present_students": set(),
            "dates": [],
        }
    )

    # Process all attendance records - each record represents a present student
    for record in attendance_records.select_related("cohort", "student").order_by(
        "date"
    ):
        week = record.week_number  # Calculated property from date

        # Apply week filter in Python (since week_number is a property)
        if selected_week and week != selected_week:
            continue

        weeks_data[week]["week_number"] = week
        weeks_data[week]["unique_students"].add(record.student.email)
        weeks_data[week]["present_students"].add(record.student.email)
        weeks_data[week]["dates"].append(record.date)

    # Calculate attendance rate and date ranges for each week
    for week, data in weeks_data.items():
        # Count unique students who were present
        data["total_count"] = len(data["unique_students"])
        data["present_count"] = len(data["present_students"])

        # Calculate week date range from actual attendance record dates
        if data["dates"]:
            data["start_date"] = min(data["dates"])
            data["end_date"] = max(data["dates"])

        # Remove sets and dates list from data (not JSON serializable)
        del data["unique_students"]
        del data["present_students"]
        del data["dates"]

    # Convert to sorted list
    weeks_list = sorted(weeks_data.values(), key=lambda x: x["week_number"])

    # Calculate overall statistics - count unique students across ALL records (not just filtered)
    all_unique_students = set(
        Attendance.objects.select_related("student").values_list(
            "student__email", flat=True
        )
    )
    total_enrolled_students = len(all_unique_students)

    # For filtered view, count unique students in filtered records
    present_students = set(attendance_records.values_list("student__email", flat=True))
    total_present = len(present_students)

    overall_attendance_rate = (
        round((total_present / total_enrolled_students * 100), 1)
        if total_enrolled_students > 0
        else 0
    )

    # Recalculate attendance rate for each week based on total enrolled students
    for data in weeks_list:
        if total_enrolled_students > 0:
            data["attendance_rate"] = round(
                (data["present_count"] / total_enrolled_students) * 100, 1
            )
        else:
            data["attendance_rate"] = 0

    # Get unique weeks and cohorts for filters (from all records, not filtered)
    # Calculate available weeks from dates since week_number is a property
    all_records = Attendance.objects.all()
    available_weeks = sorted(set(record.week_number for record in all_records))
    cohorts = Cohort.objects.all()

    context = {
        "weeks_data": weeks_list,
        "total_enrolled_students": total_enrolled_students,  # Total students across all weeks
        "total_present": total_present,
        "overall_attendance_rate": overall_attendance_rate,
        "available_weeks": available_weeks,
        "cohorts": cohorts,
        "selected_cohort": int(selected_cohort) if selected_cohort else None,
        "selected_week": int(selected_week) if selected_week else None,
    }
    return render(request, "app/attendance.html", context)


@login_required
def attendance_list(request):
    """Display student attendance records - requires staff access"""
    if request.user.is_staff:
        messages.error(request, "You do not have permission to view this page.")
        return redirect("home")
    
    student = Student.objects.filter(user=request.user).first()

    if request.method == "POST":
        attendance, created = Attendance.objects.get_or_create(
            student=student,
            cohort=student.registrations.filter(status="APPROVED").first().cohort,
            date=datetime.date.today(),
            defaults={"hours_spent": request.POST.get("hours_spent")},
        )
        if created:
            messages.success(request, "Attendance marked successfully for {} - Week {}!".format(
                attendance.cohort.name, attendance.date.isocalendar()[1]
            ))
        else:
            attendance.hours_spent = request.POST.get("hours_spent")
            attendance.save()
            messages.success(request, "Attendance updated successfully for {} - Week {}!".format(
                attendance.cohort.name, attendance.date.isocalendar()[1]
            ))
        
    attendance_records = (
        Attendance.objects.filter(student__user=request.user)
        .select_related("student", "cohort")
        .order_by("date")
    )

    cohort = student.registrations.filter(cohort__status=Cohort.StatusChoices.ACTIVE).first()

    context = {
        "student": student,
        "cohort": cohort,
        "attendance_records": attendance_records,
    }
    return render(request, "app/attendance_list.html", context)
