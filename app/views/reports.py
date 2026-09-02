from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import render

from ..models import (
    Attendance,
    Enrollment,
    StudentGrades,
    Submission,
)


# @login_required
# @staff_member_required
# def reports(request):
#     """Reports view showing student enrollments - requires staff access"""
#     from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
#     from django.db.models import Prefetch
#     from django.http import HttpResponse

#     # Optimize query with prefetching to avoid N+1 queries
#     # - Submissions are needed for enrollment.overall_average_score
#     # - Attendance is needed for registration.session_attendance_rate
#     # - Assignments are needed for calculating scores
#     enrollments = (
#         Enrollment.objects.select_related(
#             "registration__student",
#             "course",
#             "registration",
#             "registration__cohort",
#             "certificate",
#         )
#         .prefetch_related(
#             Prefetch(
#                 "submissions",
#                 queryset=Submission.objects.select_related("assignment").filter(
#                     assigned_grade__isnull=False,
#                     assignment__max_points__isnull=False,
#                     assignment__max_points__gt=0,
#                 ),
#             ),
#             Prefetch(
#                 "registration__student__attendance",
#                 queryset=Attendance.objects.select_related("cohort"),
#             ),
#             # "course__assignments",
#         )
#         .filter(course__is_visible=True)
#         # .order_by("registration__student__full_name", "cohort__name", "course__name")
#     )

#     # Calculate unique student count
#     unique_student_count = enrollments.values("registration__student").distinct().count()

#     # Handle Excel export
#     if request.GET.get("format") == "excel":
#         from openpyxl import Workbook
#         from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
#         from openpyxl.utils import get_column_letter

#         wb = Workbook()
#         ws = wb.active
#         ws.title = "Student Enrollments"

#         # Write header row with styling
#         headers = [
#             "Student Name",
#             "Email",
#             "Cohort",
#             "Course",
#             "Attendance %",
#             "Grade %",
#             "Certificate",
#         ]
#         for col, header in enumerate(headers, start=1):
#             cell = ws.cell(row=1, column=col, value=header)
#             cell.font = Font(bold=True, color="FFFFFF")
#             cell.fill = PatternFill(
#                 start_color="4F46E5", end_color="4F46E5", fill_type="solid"
#             )
#             cell.alignment = Alignment(horizontal="center", vertical="center")

#         # Track student groupings for merging
#         row = 2
#         current_student_id = None
#         student_start_row = None

#         for enrollment in enrollments:
#             attendance = (
#                 f"{enrollment.registration.session_attendance_rate:.1f}"
#                 if enrollment.registration
#                 else "N/A"
#             )
#             grade = (
#                 f"{enrollment.overall_average_score:.1f}"
#                 if enrollment.overall_average_score is not None
#                 else "N/A"
#             )
#             certificate = "Issued" if enrollment.has_certificate else "Declined"

#             # Check if this is a new student
#             if enrollment.student.id != current_student_id:
#                 # Merge previous student cells if needed
#                 if current_student_id is not None and student_start_row < row - 1:
#                     ws.merge_cells(
#                         start_row=student_start_row,
#                         start_column=1,
#                         end_row=row - 1,
#                         end_column=1,
#                     )
#                     ws.merge_cells(
#                         start_row=student_start_row,
#                         start_column=2,
#                         end_row=row - 1,
#                         end_column=2,
#                     )
#                     # Center the merged cells
#                     ws.cell(row=student_start_row, column=1).alignment = Alignment(
#                         vertical="center"
#                     )
#                     ws.cell(row=student_start_row, column=2).alignment = Alignment(
#                         vertical="center"
#                     )

#                 # Start new student group
#                 current_student_id = enrollment.student.id
#                 student_start_row = row

#                 # Write student name and email
#                 ws.cell(row=row, column=1, value=enrollment.student.full_name)
#                 ws.cell(row=row, column=2, value=enrollment.student.email)

#             # Write course data
#             ws.cell(row=row, column=3, value=enrollment.cohort.name)
#             ws.cell(row=row, column=4, value=enrollment.course.name)
#             ws.cell(row=row, column=5, value=attendance)
#             ws.cell(row=row, column=6, value=grade)
#             ws.cell(row=row, column=7, value=certificate)

#             row += 1

#         # Merge last student cells if needed
#         if current_student_id is not None and student_start_row < row - 1:
#             ws.merge_cells(
#                 start_row=student_start_row,
#                 start_column=1,
#                 end_row=row - 1,
#                 end_column=1,
#             )
#             ws.merge_cells(
#                 start_row=student_start_row,
#                 start_column=2,
#                 end_row=row - 1,
#                 end_column=2,
#             )
#             ws.cell(row=student_start_row, column=1).alignment = Alignment(
#                 vertical="center"
#             )
#             ws.cell(row=student_start_row, column=2).alignment = Alignment(
#                 vertical="center"
#             )

#         # Auto-size columns
#         for col in range(1, 8):
#             ws.column_dimensions[get_column_letter(col)].width = 20

#         # Create response
#         response = HttpResponse(
#             content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         )
#         response["Content-Disposition"] = (
#             'attachment; filename="student_enrollments_report.xlsx"'
#         )
#         wb.save(response)

#         return response

#     # Paginate enrollments (20 per page)
#     paginator = Paginator(enrollments, settings.PER_PAGE)
#     page = request.GET.get("page", 1)

#     try:
#         enrollments_page = paginator.page(page)
#     except PageNotAnInteger:
#         enrollments_page = paginator.page(1)
#     except EmptyPage:
#         enrollments_page = paginator.page(paginator.num_pages)

#     # Calculate rowspan for student cells (for merged cells in template)
#     enrollments_list = list(enrollments_page)

#     context = {
#         "enrollments": enrollments_list,
#         "total_enrollments": enrollments.count(),
#         "total_students": unique_student_count,
#         "page_obj": enrollments_page,
#     }
#     return render(request, "app/reports.html", context)

@staff_member_required
def student_grades(request):
    # Get search query
    search_query = request.GET.get("q", "").strip()

    grades = StudentGrades.objects.filter().all()

    if search_query:
        grades = grades.filter(
            Q(student__icontains=search_query) | Q(email__icontains=search_query)
        )

    # Paginate students (20 per page)
    paginator = Paginator(grades, settings.PER_PAGE)
    page = request.GET.get("page", 1)

    try:
        grades_page = paginator.page(page)
    except PageNotAnInteger:
        grades_page = paginator.page(1)
    except EmptyPage:
        grades_page = paginator.page(paginator.num_pages)

    return render(request, "app/student_grades.html", {
        "grades": grades_page,
        "search_query": search_query,
    })

@staff_member_required
def download_grades(request):
    import os

    import pandas
    grades = StudentGrades.objects.filter().all()
    df = pandas.DataFrame(list(grades.values()))
    file_path = os.path.join(settings.MEDIA_ROOT, 'report.csv')
    df.to_csv(file_path, index=False)
    file_handle = open(file_path, 'rb')
    response = FileResponse(file_handle, as_attachment=True, filename='report.csv')
    return response
