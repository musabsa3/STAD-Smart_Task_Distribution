from django.contrib import admin
from .models import Profile, Project, Task, Skill, JobRole, EmployeeSkill, Submission, Permission, ActivityLog, TaskRating
# Register your models here.

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "job_role")
    list_filter = ("role", "job_role")
    search_fields = ('user__username', 'user__first_name')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "manager", "start_date", "end_date")
    search_fields = ("name", "description")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "assignee", "status", "due_date", "created_at")
    list_filter = ("status", "project")
    search_fields = ("title", "description")
    filter_horizontal = ("required_skills",)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("task", "employee", "submitted_at")
    list_filter = ("submitted_at",)
    search_fields = ("task__title", "employee__username")


# ------------------------
# مصعب — إضافات الموارد البشرية
# ------------------------

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ('user', 'skill', 'level')
    list_filter = ('skill', 'level')
    search_fields = ('user__username', 'skill__name')


@admin.register(JobRole)
class JobRoleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('permissions',)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action_type", "timestamp")
    list_filter = ("action_type", "timestamp")
    search_fields = ("message", "user__username")

@admin.register(TaskRating)
class TaskRatingAdmin(admin.ModelAdmin):
    list_display = ("task", "employee", "rating", "manager", "created_at")
    list_filter = ("rating", "manager")
    search_fields = ("task__title", "employee__username")

