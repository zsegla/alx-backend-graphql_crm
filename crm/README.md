# Setup for CRM Celery + Beat

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Start Redis

```bash
redis-server
```

## Run Migrations

```bash
python manage.py migrate
```

## Start Celery Worker

```bash
celery -A crm worker -l info
```

## Start Celery Beat

```bash
celery -A crm beat -l info
```

## Verify Report

Check logs in:

```bash
cat /tmp/crm_report_log.txt
```

---

Every Monday morning a new line will be appended to `/tmp/crm_report_log.txt` with customers, orders, and revenue.
