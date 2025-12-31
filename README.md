# STAD — Smart Task Distribution System

STAD is a smart task distribution web application designed to improve fairness and efficiency in assigning tasks within a workplace.

The system helps managers assign tasks manually or receive AI-assisted suggestions based on employee skills, workload, and task requirements.

## What Problem Does STAD Solve?
In many organizations, task assignment is often:
- Subjective
- Unbalanced
- Based on availability rather than capability

STAD addresses this by introducing structured task management combined with intelligent assignment suggestions.

## Key Features
- Manager & Employee dashboards
- Projects and tasks management
- Manual task assignment
- AI-assisted task assignment suggestions
- Task status tracking (To-Do, In Progress, Completed, Late)
- Employee performance tracking
- Task submissions and reviews
- Export reports to Excel

## Tech Stack
- Backend: Django (Python)
- Database: MySQL / MariaDB
- AI Integration: OpenAI API
- Frontend: Django Templates (HTML/CSS)
- Tools: Git, GitHub

## My Role
- Designed and implemented the backend logic
- Built task distribution and tracking features
- Integrated AI-based task assignment suggestions
- Designed database models and relationships
- Managed project structure and version control

## Setup (Local Development)
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
