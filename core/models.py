from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class Profile(models.Model):
    ROLE_CHOICES = (
        ('manager', 'Manager'),
        ('employee', 'Employee'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # الدور العام داخل النظام (مدير / موظف)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='employee'
    )

    # المسمى الوظيفي (Backend Developer, UI/UX Designer, Project Manager...)
    job_role = models.ForeignKey(
        'JobRole',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='s'
    )

    current_workload = models.IntegerField(default=0)

    overall_rating = models.FloatField(default=0.0)

    rating_count = models.PositiveIntegerField(default=0)

    def calculate_workload(self):
        """
        يحسب عبء العمل الحقيقي للموظف:
        - المهام in_progress و late فقط
        - normal = 1
        - medium = 2
        - heavy = 3
        """
        from .models import Task

        active_status = ["in_progress", "late" , "todo"]

        tasks = Task.objects.filter(
            assignee=self.user,
            status__in=active_status
        )

        workload = 0

        for task in tasks:
            if hasattr(task, "impact"):
                if task.impact == "medium":
                    workload += 2
                elif task.impact == "heavy":
                    workload += 3
                else:
                    workload += 1
            else:
                workload += 1

        return workload
    

    # لحساب الضغط لاحقًا (Cache field)
    #def calculate_workload(self):
        #active = ["todo", "in_progress", "blocked"]
        #from .models import Task  # تجنب الـ circular import
        #return Task.objects.filter(
            #assignee=self.user,
            #status__in=active
        #).count()
    
    def __str__(self):
        job_title = self.job_role.name if self.job_role else "No Job Role"
        return f"{self.user.username} - {self.get_role_display()} ({job_title})"


class Project(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_projects'
    )

    def __str__(self):
        return self.name


class Permission(models.Model):
    name = models.CharField(max_length=150)
    

    def __str__(self):
        return self.name
    

class JobRole(models.Model):
    name = models.CharField(max_length=150, unique=True)
    permissions = models.ManyToManyField('Permission', blank=True, related_name='roles')

    def __str__(self):
        return self.name

    
    
#المهارات المطلوبة للتاسك
class Skill(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name

#مهارات الموظف
class EmployeeSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_set")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    level = models.IntegerField(default=1)   # المستوى من 1–5

    def __str__(self):
        return f"{self.user.username} - {self.skill.name} ({self.level})"


    
    
class Task(models.Model):
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ("under_review", "Under Review"),
        ('blocked', 'Blocked'),
        ('completed', 'Completed'),
        ("late", "Late"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks',
        null=True,
        blank=True,
    )

    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )

    

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='todo'
    )

    due_date = models.DateField(null=True, blank=True)
    required_skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="tasks_required"
    )

    IMPACT_CHOICES = [
        ('normal', 'عادية'),
        ('medium', 'متوسطة'),
        ('heavy', 'ثقيلة'),
    ]

    impact = models.CharField(
    max_length=10,
    choices=IMPACT_CHOICES,
    default='normal'
    )
    
    PRIORITY_CHOICES = [
    ('low', 'منخفضة'),
    ('medium', 'متوسطة'),
    ('high', 'عالية'),
    ]

    priority = models.CharField(
    max_length=10,
    choices=PRIORITY_CHOICES,
    default='medium'
    )
    


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Submission(models.Model):
    STATUS_CHOICES = [
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    notes = models.TextField(blank=True)
    attachment = models.FileField(upload_to='submissions/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='under_review'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_submissions'
    )
    
    # ✅ التقييم والملاحظات (لكل تسليم)
    rating = models.IntegerField(null=True, blank=True)
    manager_comment = models.TextField(blank=True)

    def __str__(self):
        return f"Submission by {self.employee.username} for {self.task.title}"
    
    def get_rating(self):
        """ترجع التقييم المباشر من Submission"""
        return self.rating
    
    def get_rating_comment(self):
        """ترجع ملاحظات المدير المباشرة من Submission"""
        return self.manager_comment
    

class TaskRating(models.Model):
    """
    تقييم الموظف على مهمة معيّنة
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="ratings"
    )
    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="task_ratings"
    )
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="given_ratings"
    )

    # التقييم من 1 إلى 5 نجوم
    rating = models.PositiveSmallIntegerField()

    # ملاحظات المدير (اختياري)
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("task", "employee")  # ما فيه تقييمين لنفس الموظف على نفس المهمة

    def __str__(self):
        return f"{self.task.title} - {self.employee.username} ({self.rating}★)"



class ActivityLog(models.Model):
    ACTION_TYPES = [
    ("project_created", "تم إنشاء مشروع جديد"),
    ("task_created", "تم إنشاء مهمة جديدة"),
    ("task_updated", "تم تحديث مهمة"),
    ("task_completed", "تم اكتمال مهمة"),
    ("submission_added", "تم رفع تسليم"),
    ("submission_approved", "تمت الموافقة على تسليم"),  # ✅ جديد
    ("submission_rejected", "تم رفض تسليم"),  # ✅ جديد
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} – {self.action_type} – {self.timestamp}"

