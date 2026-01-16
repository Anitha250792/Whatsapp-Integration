from django.shortcuts import redirect

def google_login_success(request):
    # Google login already created session
    return redirect("http://localhost:5173/dashboard")
