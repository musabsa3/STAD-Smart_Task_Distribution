from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models import Avg, Count
from .models import Task, Profile, Submission, Project, ActivityLog, TaskRating



# ======================
# تحديث ضغط العمل
# ======================
def update_profile_workload(user):
    profile = Profile.objects.filter(user=user).first()
    if profile:
        new_value = profile.calculate_workload()  # ← الدالة الجديدة داخل Profile
        profile.current_workload = new_value
        profile.save(update_fields=["current_workload"])



def recalculate_overall_rating(user):
    """
    يعيد حساب متوسط تقييم الموظف وعدد التقييمات
    بناءً على جدول TaskRating
    """
    profile = Profile.objects.filter(user=user).first()
    if not profile:
        return

    qs = TaskRating.objects.filter(employee=user)

    agg = qs.aggregate(
        avg=Avg("rating"),
        count=Count("id"),
    )

    profile.overall_rating = agg["avg"] or 0.0
    profile.rating_count = agg["count"] or 0
    profile.save(update_fields=["overall_rating", "rating_count"])



# ======================
# نشاط المهام
# ======================
@receiver(post_save, sender=Task)
def task_activity(sender, instance, created, **kwargs):

    # تحديث الضغط
    if instance.assignee:
        update_profile_workload(instance.assignee)

    # ===== تسجيل الأنشطة =====
    user = instance.assignee  # قد يكون None

    if created:
        ActivityLog.objects.create(
            user=user,
            action_type="task_created",
            message=f"تم إنشاء مهمة جديدة: {instance.title}"
        )
    else:
        if instance.status == "completed":
            ActivityLog.objects.create(
                user=user,
                action_type="task_completed",
                message=f"تم اكتمال مهمة: {instance.title}"
            )
        else:
            ActivityLog.objects.create(
                user=user,
                action_type="task_updated",
                message=f"تم تحديث مهمة: {instance.title}"
            )


@receiver(post_delete, sender=Task)
def task_deleted(sender, instance, **kwargs):
    if instance.assignee:
        update_profile_workload(instance.assignee)
    # حذف المهمة لا يسجل Activity الآن (حسب رغبتك)


# ======================
# نشاط التسليمات
# ======================
@receiver(post_save, sender=Submission)
def submission_added(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.employee,
            action_type="submission_added",
            message=f"{instance.employee.username} رفع تسليم لمهمة: {instance.task.title}"
        )

    update_profile_workload(instance.employee)

@receiver(post_save, sender=TaskRating)
def task_rating_saved(sender, instance, created, **kwargs):
    # كل ما ينحفظ تقييم (جديد أو تعديل) نعيد حساب تقييم الموظف
    recalculate_overall_rating(instance.employee)


@receiver(post_delete, sender=TaskRating)
def task_rating_deleted(sender, instance, **kwargs):
    # لو انحذف تقييم، نعيد الحساب برضو
    recalculate_overall_rating(instance.employee)


# ======================
# تسجيل نشاط المشاريع
# ======================
@receiver(post_save, sender=Project)
def project_created(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.manager,
            action_type="project_created",
            message=f"تم إنشاء مشروع جديد: {instance.name}"
        )


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)