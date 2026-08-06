import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select, func

from app.db import init_db, Session, engine
from app.models import DailyRecord, FoodEntry, WeightMeasurement, AuditLog
from app.services.history_importer import import_history

init_db()

with Session(engine) as s:
    dry = import_history(s, format="json", dry_run=True)
    print("DRY RUN  -> inserted=%d skipped=%d errors=%d" % (dry.inserted, dry.skipped, dry.errors))

    real = import_history(s, format="json", dry_run=False)
    print("REAL     -> inserted=%d skipped=%d errors=%d" % (real.inserted, real.skipped, real.errors))

    total = s.exec(select(func.count()).select_from(DailyRecord)).one()
    locked = s.exec(select(func.count()).select_from(DailyRecord).where(DailyRecord.is_locked == 1)).one()
    foods = s.exec(select(func.count()).select_from(FoodEntry)).one()
    weights = s.exec(select(func.count()).select_from(WeightMeasurement)).one()
    audits = s.exec(select(func.count()).select_from(AuditLog)).one()
    print("COUNTS   -> records=%d locked=%d foods=%d weights=%d audits=%d"
          % (total, locked, foods, weights, audits))

    again = import_history(s, format="json", dry_run=False)
    print("2ND RUN  -> inserted=%d skipped=%d errors=%d (idempotency check)"
          % (again.inserted, again.skipped, again.errors))

    sample = s.exec(select(DailyRecord).where(DailyRecord.record_date == "2026-06-18")).first()
    print("SAMPLE 06-18 -> locked=%d status=%s kcal=[%s,%s] period_day=%s"
          % (sample.is_locked, sample.data_status, sample.total_kcal_min, sample.total_kcal_max, sample.period_day))
    fe = s.exec(select(FoodEntry).where(FoodEntry.daily_record_id == sample.id)).all()
    print("  06-18 meals:", [(f.meal_type, f.food_name[:12]) for f in fe])
