from django.shortcuts import render
from django.db.models import Avg
from classification.models import Classification
from products.models import Product
from dashboard.models import ProcessingJob
from taxonomy.models import TaxonomyCategory
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

@login_required(login_url='login')
def dashboard_home(request):
    total_products = Product.objects.count()
    classified_products = Classification.objects.count()
    needs_review = Classification.objects.filter(requires_manual_review=True).count()
    failed_products = Classification.objects.filter(status='FAILED').count()
    
    # Calculate average confidence
    avg_conf = Classification.objects.aggregate(Avg('confidence'))['confidence__avg'] or 0
    
    # Get the latest processing job
    latest_job = ProcessingJob.objects.order_by('-start_time').first()
    
    
    # Get all categories for manual selection when AI fails
    all_categories = TaxonomyCategory.objects.all().values('id', 'name', 'full_path')
    all_categories_json = json.dumps(list(all_categories))
    
    context = {
        'total_products': total_products,
        'classified_products': classified_products,
        'pending_products': total_products - classified_products,
        'needs_review': needs_review,
        'failed_products': failed_products,
        'avg_confidence': round(avg_conf, 2),
        'latest_job': latest_job,
        'all_categories': all_categories_json,
    }
    return render(request, 'dashboard/index.html', context)

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect('dashboard_home')
        else:
            return render(request, 'dashboard/login.html', {'error': 'Invalid credentials.'})
    return render(request, 'dashboard/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')
