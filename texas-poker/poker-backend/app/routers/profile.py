from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/profile", tags=["profile"])

@router.get("/battle-records", response_model=List[schemas.BattleRecordResponse])
def get_battle_records(
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    records = db.query(models.BattleRecord).filter(
        models.BattleRecord.user_id == current_user.id
    ).order_by(models.BattleRecord.created_at.desc()).offset(skip).limit(limit).all()
    
    return records

@router.get("/statistics")
def get_user_statistics(
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    total_games = db.query(models.BattleRecord).filter(
        models.BattleRecord.user_id == current_user.id
    ).count()
    
    total_wins = db.query(models.BattleRecord).filter(
        models.BattleRecord.user_id == current_user.id,
        models.BattleRecord.is_winner == True
    ).count()
    
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
    
    total_profit = db.query(models.BattleRecord).filter(
        models.BattleRecord.user_id == current_user.id
    ).with_entities(db.func.sum(models.BattleRecord.profit)).scalar() or 0
    
    props_used = db.query(models.PropUsage).filter(
        models.PropUsage.user_id == current_user.id
    ).count()
    
    props_cost = db.query(models.PropUsage).filter(
        models.PropUsage.user_id == current_user.id
    ).with_entities(db.func.sum(models.PropUsage.cost)).scalar() or 0
    
    return {
        "total_games": total_games,
        "total_wins": total_wins,
        "win_rate": round(win_rate, 2),
        "total_profit": total_profit,
        "current_coins": current_user.coins,
        "props_used": props_used,
        "props_total_cost": props_cost
    }

@router.post("/daily-signin")
def daily_signin(
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    today = datetime.utcnow().date()
    
    existing_task = db.query(models.DailyTask).filter(
        models.DailyTask.user_id == current_user.id,
        models.DailyTask.task_type == "daily_signin",
        db.func.date(models.DailyTask.date) == today
    ).first()
    
    if existing_task:
        raise HTTPException(status_code=400, detail="Already signed in today")
    
    reward = 50
    current_user.coins += reward
    
    task = models.DailyTask(
        user_id=current_user.id,
        task_type="daily_signin",
        completed=True,
        reward_coins=reward
    )
    db.add(task)
    db.commit()
    
    return {
        "success": True,
        "reward": reward,
        "new_balance": current_user.coins
    }
