from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from ..models import (
    Student
)



@login_required
def profile(request):
    """Student profile view - allows students to edit their name"""
    
    # Get student profile for logged-in user
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        # No student profile - redirect to home (which shows registration options)
        messages.info(request, 'Please register for a cohort to access your profile.')
        return redirect('home')
    
    # Block staff from editing student profiles
    if request.user.is_staff:
        messages.error(request, 'Staff members cannot access student profiles.')
        return redirect('home')
    
    # Handle profile update (POST request)
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        given_name = request.POST.get('given_name', '').strip()
        family_name = request.POST.get('family_name', '').strip()
        unique_id = request.POST.get('unique_id', '').strip()
        city = request.POST.get('city', '').strip()
        
        if full_name:
            student.full_name = full_name
            student.given_name = given_name
            student.family_name = family_name
            student.unique_id = unique_id  # Assuming unique_id is also being updated from the form
            student.city = city
            student.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Full name is required.')
    
    context = {
        'student': student,
    }
    return render(request, 'app/profile.html', context)