@echo off
echo ========================================================
echo Starting Shopify Taxonomy Classifier (Local Environment)
echo ========================================================

echo 1. Starting Redis Server...
start "Redis Server" cmd /k "redis-server"

echo 2. Starting Celery Worker...
start "Celery Worker" cmd /k "celery -A config worker -l info --pool=threads"

echo 3. Ensuring default admin user exists...
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')"

echo 4. Starting Django Server...
start "Django Server" cmd /k "python manage.py runserver"

echo.
echo Setup Complete! 
echo All three services have been launched in separate terminal windows.
echo You can access the dashboard at: http://127.0.0.1:8000/dashboard/
echo ========================================================
