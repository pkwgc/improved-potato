from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/users", response_model=List[schemas.User])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(auth.get_admin_user),
    db: Session = Depends(get_db)
):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    update: schemas.AdminUserUpdate,
    current_user: models.User = Depends(auth.get_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if update.coins is not None:
        user.coins = update.coins
    if update.points is not None:
        user.points = update.points
    if update.win_rate_adjustment is not None:
        user.win_rate_adjustment = update.win_rate_adjustment
    if update.is_active is not None:
        user.is_active = update.is_active
    
    db.commit()
    db.refresh(user)
    return user

@router.get("/statistics")
def get_statistics(
    current_user: models.User = Depends(auth.get_admin_user),
    db: Session = Depends(get_db)
):
    total_users = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.is_active == True).count()
    
    today = datetime.utcnow().date()
    dau = db.query(models.User).filter(
        models.User.last_login >= datetime.combine(today, datetime.min.time())
    ).count()
    
    total_games = db.query(models.Game).count()
    active_games = db.query(models.Game).filter(
        models.Game.status == models.GameStatus.PLAYING
    ).count()
    
    total_props_used = db.query(models.PropUsage).count()
    total_props_revenue = db.query(models.PropUsage).with_entities(
        db.func.sum(models.PropUsage.cost)
    ).scalar() or 0
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "daily_active_users": dau,
        "total_games": total_games,
        "active_games": active_games,
        "total_props_used": total_props_used,
        "total_props_revenue": total_props_revenue
    }

@router.get("/prop-usage")
def get_prop_usage_stats(
    current_user: models.User = Depends(auth.get_admin_user),
    db: Session = Depends(get_db)
):
    view_others = db.query(models.PropUsage).filter(
        models.PropUsage.prop_type == models.PropType.VIEW_OTHERS_CARDS
    ).count()
    
    view_future = db.query(models.PropUsage).filter(
        models.PropUsage.prop_type == models.PropType.VIEW_FUTURE_CARDS
    ).count()
    
    return {
        "view_others_cards": view_others,
        "view_future_cards": view_future
    }

@router.post("/cleanup-old-records")
def cleanup_old_records(
    current_user: models.User = Depends(auth.get_admin_user),
    db: Session = Depends(get_db)
):
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    
    deleted = db.query(models.BattleRecord).filter(
        models.BattleRecord.created_at < cutoff_date
    ).delete()
    
    db.commit()
    
    return {"deleted_records": deleted}
