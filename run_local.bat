@echo off
echo ========================================================
echo Starting Shopify Taxonomy Classifier (Local Environment)
echo ========================================================

echo 1. Starting Redis Server...
start "Redis Server" cmd /k "redis-server"

echo 2. Starting Celery Worker...
start "Celery Worker" cmd /k "celery -A core worker -l info --pool=threads"

echo 3. Starting Django Server...
start "Django Server" cmd /k "python manage.py runserver"

echo.
echo Setup Complete! 
echo All three services have been launched in separate terminal windows.
echo You can access the dashboard at: http://127.0.0.1:8000/dashboard/
echo ========================================================
