from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),    
    path('register/', views.register_view, name='register'), 
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path("projects/create/", views.create_project, name="create_project"),
    path('projects/<int:project_id>/edit/', views.edit_project, name='edit_project'),
    path('projects/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    

    path('tasks/create/', views.create_task, name='create_task'), 
    path("tasks/<int:task_id>/edit/", views.edit_task, name="edit_task"),
    path("tasks/<int:task_id>/delete/", views.delete_task, name="delete_task"),

    path('tasks/submit/', views.submit_task, name='submit_task'),
    path("tasks/<int:task_id>/start/", views.start_task, name="start_task"),

    # ===== صفحة التسليمات =====
    path('submissions/', views.submissions_view, name='submissions'),
    path('submissions/<int:submission_id>/approve/', views.approve_submission, name='approve_submission'),
    path('submissions/<int:submission_id>/reject/', views.reject_submission, name='reject_submission'),

    path("test-ai/", views.test_ai_view, name="test_ai"),
    path("api/smart-assign/", views.smart_assign_api, name="smart_assign_api"),

     # ===== تصدير البيانات =====
    path('export/employees/', views.export_employees_excel, name='export_employees_excel'),
    path('export/tasks/', views.export_tasks_excel, name='export_tasks_excel'),
    path('export/submissions/', views.export_submissions_excel, name='export_submissions_excel'),

    

    





]
