from openai import OpenAI
from django.conf import settings

from django.contrib.auth.models import User
from .models import Task, Profile, EmployeeSkill, Skill
import json
import re

# إنشاء الكلاينت مرة وحدة
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def _map_workload_impact_value(impact_code: str | None) -> int:
    """
    يحوّل كود تأثير المهمة إلى رقم:
    normal → 1, medium → 2, heavy → 3
    """
    if impact_code is None:
        return 1
    mapping = {
        "normal": 1,   # عادية
        "medium": 2,   # متوسطة
        "heavy": 3,    # ثقيلة
    }
    return mapping.get(impact_code, 1)


def _extract_text_from_response(response) -> str:
    """
    دالة مساعدة عشان نطلع النص من response حق OpenAI
    بدون ما نتعقّد لو تغير الشكل شوي.
    """
    out = response.output[0].content[0]
    text = getattr(out, "text", out)
    text = getattr(text, "value", str(text))
    return text


def chat_with_stad_ai(message: str) -> str:
    """
    دالة بسيطة قديمة (للاختبار) ترسل برومبت لـ OpenAI وترجع رد عادي.
    تستخدم في test_ai_view.
    """
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=message,
        )
        reply_text = _extract_text_from_response(response)
        return reply_text
    except Exception as e:
        return f"ERROR from OpenAI: {e}"


# ==============================
# 1) بناء JSON من بيانات النظام
# ==============================

def build_candidates_list():
    """
    ترجع قائمة كل الموظفين مع بياناتهم اللي نستخدمها في التوزيع الذكي:
    - المهارات
    - المسمى الوظيفي
    - الصلاحيات المستخرجة من الـ job_role
    """
    profiles = (
        Profile.objects
        .filter(role="employee")
        .select_related("user", "job_role")
        .prefetch_related("user__skill_set__skill", "job_role__permissions")
    )

    candidates = []
    for profile in profiles:
        user = profile.user

        # ✅ مهارات الموظف
        skills = [
            {
                "skill_id": es.skill.id,
                "skill_name": es.skill.name,
                "level": es.level,
            }
            for es in user.skill_set.all()
        ]

        # ✅ صلاحيات الوظيفة (job_role.permissions)
        permissions = []
        if profile.job_role:
            permissions = [
                perm.name for perm in profile.job_role.permissions.all()
            ]

        candidates.append(
            {
                "user_id": user.id,
                "name": user.get_full_name() or user.username,
                "job_role": profile.job_role.name if profile.job_role else None,
                "permissions": permissions,          # 👈 مضافة جديدة
                "current_workload": profile.current_workload,
                "overall_rating": profile.overall_rating,
                "rating_count": profile.rating_count,
                "skills": skills,
            }
        )

    print("\n\nCANDIDATES DEBUG OUTPUT:\n", json.dumps(candidates, ensure_ascii=False, indent=2), "\n\n")
    return candidates




def build_task_context(task: Task) -> dict:
    """
    تستخدم لما تكون المهمة محفوظة في الداتابيس.
    تبني JSON فيه:
    - معلومات المهمة
    - قائمة المرشحين (من build_candidates_list)
    """
    required_skills = [
        {"id": s.id, "name": s.name}
        for s in task.required_skills.all()
    ]

    impact_value = _map_workload_impact_value(getattr(task, "impact", None))

    context = {
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "project": task.project.name if task.project else None,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "required_skills": required_skills,
            "priority": getattr(task, "priority", "medium"),  
            "workload_impact_value": impact_value, 
        },
        "candidates": build_candidates_list(),  # ✅ هنا استخدمنا الدالة الجديدة
    }

    return context



def debug_task_context(task: Task):
    """
    دالة بس تطبع JSON في الكونسل عشان تشوف شكله قبل ربط AI.
    تقدر تستدعيها من Django shell.
    """
    ctx = build_task_context(task)
    print(json.dumps(ctx, ensure_ascii=False, indent=2))


# ==============================
# 2) خوارزمية STAD مع OpenAI
# ==============================

def _call_stad_ai_assignment(context: dict) -> dict:
    """
    تستقبل context (task + candidates) وترسلها لـ OpenAI
    وترجع JSON فيه assigned_user_id + reason + scores.
    تستخدمها أكثر من دالة (من نموذج حقيقي أو من فورم).
    """
    system_prompt = """
You are STAD, an AI agent that assigns tasks to employees in a company.

You receive a JSON object with:
{
  "task": {
    "id": int or null,
    "title": str,
    "description": str,
    "project": str or null,
    "due_date": ISO date string or null,
    "required_skills": [
      {"id": int, "name": str}
    ],
    "priority": "low" | "medium" | "high",
    "workload_impact_value": int   // 1 (normal), 2 (medium), 3 (heavy)
  },
  "candidates": [
    {
      "user_id": int,
      "name": str,
      "job_role": str or null,
      "permissions": [str],
      "current_workload": int,
      "overall_rating": float,
      "rating_count": int,
      "skills": [
        {
          "skill_id": int,
          "skill_name": str,
          "level": int
        }
      ]
    }
  ]
}

------------------------------------------------------------
TASK VALIDATION RULES (EXTREMELY IMPORTANT)
------------------------------------------------------------

Before scoring or selecting any candidate, validate the task:

1) INVALID OR NONSENSE TITLES / DESCRIPTIONS
   A task is INVALID if:
   - The title or description contains repeated characters like "000000", "aaaaaa", "$$$$".
   - The text is random, unreadable, or gibberish.
   - The text is extremely short or meaningless ("test", "xyz", "??", "…").
   - The text does not describe any real action or purpose.

   If INVALID:
     Return EXACTLY:
     {
       "assigned_user_id": null,
       "reason": "خطأ: عنوان المهمة أو وصفها غير واضح أو غير قابل للفهم.",
       "scores": []
     }

2) NON-IT / OUT-OF-SCOPE TASKS
   If the task clearly belongs outside the IT department, such as:
   - تنظيم اجتماع
   - فعالية / event
   - حجز فندق / مطعم
   - ترتيبات إدارية أو لوجستية
   - أي نشاط لا علاقة له بعمل قسم التقنية

   Then return EXACTLY:
     {
       "assigned_user_id": null,
       "reason": "خطأ: المهمة ليست ضمن نطاق عمل قسم التقنية ولا يمكن إسنادها.",
       "scores": []
     }

3) DOMAIN – SKILL CONSISTENCY CHECK
   Infer the domain from title + description:
   - Data / Analytics / SQL → data domain
   - Backend / APIs → backend domain
   - UI/UX → design domain
   - DevOps / Deployment → infra domain
   - Cybersecurity → security domain

   If required_skills clearly contradict the inferred domain:
     Example:
       title: "تحليل بيانات باستخدام SQL"
       required_skill: "Cybersecurity"
     → This is a strong mismatch.

   If mismatch is STRONG:
     Return EXACTLY:
     {
       "assigned_user_id": null,
       "reason": "خطأ: المهارات المطلوبة لا تتطابق مع طبيعة المهمة المذكورة في العنوان والوصف.",
       "scores": []
     }

   If mismatch is mild:
     → TRUST the domain inferred from title/description MORE than required_skills.

   SPECIAL NOTE FOR DATA DOMAIN:
     - If the task is about data analysis, reports, dashboards:
         prefer Data Analyst, BI Analyst over Data Engineer.
     - If the task is about pipelines, ETL, performance tuning:
         prefer Data Engineer over Data Analyst.

------------------------------------------------------------
SCORING LOGIC (USED ONLY IF TASK IS VALID)
------------------------------------------------------------

1) Skill Match (IMPORTANT BUT DOMAIN-AWARE)
   - Compare required_skills with candidate.skills by skill_name.
   - Missing skills strongly reduce scoring.
   - But DO NOT reward a skill that contradicts the domain.
     (e.g., do NOT select a Cybersecurity Engineer for a clear SQL data analysis task.)

2) Permissions Match (CRITICAL SAFETY)
   Infer needed permissions from title/description:
   - "deploy", "production", "CI/CD" → deploy_infrastructure, manage_ci_cd
   - "logs", "monitoring" → access_logs
   - "API", "endpoint" → manage_apis, debug_code
   - "database", "schema" → modify_database, query_data
   - "security", "vulnerability" → manage_security

   - Missing a critical permission → very low score or unsuitable.
   - Permissions DO NOT matter for non-IT tasks (but those tasks already return error).

3) Job Role Fit
   - MUST match the inferred domain.
   - Mismatched roles → strong penalty.
   - For data tasks:
       * Analysis → Data Analyst > Data Engineer
       * Pipelines → Data Engineer > Data Analyst

4) Base Workload
   - Lower workload preferred if skills are similar.

5) Workload Impact
   - adjusted = current_workload + workload_impact_value
   - Avoid assigning heavy tasks to overloaded candidates.

6) Priority
   - High: skills + permissions matter more.
   - Low: workload balance matters more.

7) Rating
   - Prefer higher rating when candidates are otherwise similar.

8) Invalid Candidates
   - If a candidate has zero relevant skills *and* zero relevant permissions → score ≈ 0.0.

------------------------------------------------------------
VERY IMPORTANT OUTPUT RULES
------------------------------------------------------------

Return ONLY valid JSON with this structure:

{
  "assigned_user_id": <int or null>,
  "reason": "<Arabic explanation>",
  "scores": [
    {"user_id": <int>, "score": <float 0–1>}
  ]
}

- If returning an ERROR (invalid title, non-IT, or domain mismatch):
  * assigned_user_id MUST be null
  * reason MUST be in Arabic
  * scores MUST be an empty list []

- No markdown, no ``` , no extra text.
- Output ONLY the JSON object.

ABOUT "reason":
- Must be SHORT, CLEAR, and in BULLETED FORM.
- Every bullet MUST be a single, short sentence.
- Use only the core evaluation factors:
    • تطابق المهارات المطلوبة بالمستوى.
    • امتلاك الصلاحيات المناسبة للمهمة.
    • ملاءمة الدور الوظيفي مع مجال المهمة.
    • عبء العمل الحالي بعد إضافة المهمة.
    • التقييم العام للموظف.
- DO NOT include story-like text.
- DO NOT repeat the task description.
- DO NOT include unnecessary details.
- DO NOT merge bullets—each factor must be in a separate bullet.

Example style (NOT exact content):
"- يمتلك مهارة SQL المطلوبة للمهمة
- لديه صلاحيات query_data المناسبة
- دوره كمحلل بيانات مناسب لطبيعة المهمة
- عبء العمل لديه منخفض مقارنة بالمرشحين الآخرين
- تقييمه العام جيد مما يعزز موثوقيته"

The final reason MUST follow this exact simple style.
"""


    user_prompt = "Here is the task and candidate list as JSON:\n" + json.dumps(
        context, ensure_ascii=False
    )

    response = client.responses.create(
        model="gpt-4.1-mini",
        temperature=0,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_text = _extract_text_from_response(response)

    # نحاول نحوله لـ JSON
    try:
        data = json.loads(raw_text)
    except Exception:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not match:
            raise ValueError(f"AI returned non-JSON text: {raw_text}")
        data = json.loads(match.group(0))

    return data



def suggest_assignee_for_task(task: Task) -> dict:
    """
    نسخة تستخدم لما تكون المهمة محفوظة فعلاً في الداتابيس.
    """
    context = build_task_context(task)
    return _call_stad_ai_assignment(context)

def suggest_assignee_for_form_input(
    title: str,
    description: str,
    due_date: str | None,
    required_skill_ids: list[int],
    priority: str = "medium",          
    impact: str | None = "normal",     
) -> dict:
    """
    تُستخدم في شاشة إنشاء المهمة (قبل الحفظ).
    تستقبل بيانات الفورم فقط وترجع نفس الـ JSON:
    { assigned_user_id, reason, scores }
    """

    skills_qs = Skill.objects.filter(id__in=required_skill_ids)
    required_skills = [
        {"id": s.id, "name": s.name}
        for s in skills_qs
    ]

    impact_value = _map_workload_impact_value(impact)

    task_payload = {
        "id": None,
        "title": title,
        "description": description,
        "project": None,  # ما عندنا مشروع محدد من الفورم لو ما ارسلناه
        "due_date": due_date,  # string مثل "2025-12-31" أو None
        "required_skills": required_skills,
        "priority": priority,            
        "workload_impact_value": impact_value, 
    }

    context = {
        "task": task_payload,
        "candidates": build_candidates_list(),
    }

    return _call_stad_ai_assignment(context)


