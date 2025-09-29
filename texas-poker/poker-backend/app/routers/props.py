from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from ..database import get_db
from ..game_manager import game_manager
from ..poker_logic import Card

router = APIRouter(prefix="/api/props", tags=["props"])

PROP_COSTS = {
    models.PropType.VIEW_OTHERS_CARDS: 100,
    models.PropType.VIEW_FUTURE_CARDS: 150
}

@router.post("/use")
def use_prop(
    prop_use: schemas.PropUse,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    cost = PROP_COSTS.get(prop_use.prop_type)
    if not cost:
        raise HTTPException(status_code=400, detail="Invalid prop type")
    
    if current_user.coins < cost:
        raise HTTPException(status_code=400, detail="Insufficient coins")
    
    game = db.query(models.Game).filter(models.Game.id == prop_use.game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game.status != models.GameStatus.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")
    
    player = db.query(models.GamePlayer).filter(
        models.GamePlayer.game_id == prop_use.game_id,
        models.GamePlayer.user_id == current_user.id
    ).first()
    if not player:
        raise HTTPException(status_code=400, detail="Not in this game")
    
    usage_count = db.query(models.PropUsage).filter(
        models.PropUsage.user_id == current_user.id,
        models.PropUsage.game_id == prop_use.game_id,
        models.PropUsage.prop_type == prop_use.prop_type
    ).count()
    
    if prop_use.prop_type == models.PropType.VIEW_OTHERS_CARDS and usage_count >= 1:
        raise HTTPException(status_code=400, detail="Already used this prop in this game")
    
    if prop_use.prop_type == models.PropType.VIEW_FUTURE_CARDS and usage_count >= 2:
        raise HTTPException(status_code=400, detail="Maximum 2 uses per game")
    
    if prop_use.prop_type == models.PropType.VIEW_FUTURE_CARDS:
        if game.current_round not in ["flop", "turn"]:
            raise HTTPException(status_code=400, detail="Can only use during flop or turn")
    
    current_user.coins -= cost
    
    target_info = {}
    
    if prop_use.prop_type == models.PropType.VIEW_OTHERS_CARDS:
        if not prop_use.target_player_id:
            raise HTTPException(status_code=400, detail="Target player required")
        
        target_player = db.query(models.GamePlayer).filter(
            models.GamePlayer.game_id == prop_use.game_id,
            models.GamePlayer.user_id == prop_use.target_player_id
        ).first()
        
        if not target_player:
            raise HTTPException(status_code=400, detail="Target player not found")
        
        if target_player.is_folded:
            raise HTTPException(status_code=400, detail="Target player has folded")
        
        target_info = {
            "target_player_id": prop_use.target_player_id,
            "cards": target_player.hole_cards
        }
    
    elif prop_use.prop_type == models.PropType.VIEW_FUTURE_CARDS:
        poker_game = game_manager.get_game(prop_use.game_id)
        if poker_game and len(poker_game.deck.cards) > 0:
            next_card = poker_game.deck.cards[0]
            target_info = {
                "next_card": next_card.to_dict()
            }
        else:
            target_info = {"next_card": None}
    
    prop_usage = models.PropUsage(
        user_id=current_user.id,
        game_id=prop_use.game_id,
        prop_type=prop_use.prop_type,
        cost=cost,
        target_info=target_info
    )
    db.add(prop_usage)
    db.commit()
    
    return {
        "success": True,
        "prop_type": prop_use.prop_type,
        "cost": cost,
        "remaining_coins": current_user.coins,
        "info": target_info
    }

@router.get("/history")
def get_prop_history(
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    history = db.query(models.PropUsage).filter(
        models.PropUsage.user_id == current_user.id
    ).order_by(models.PropUsage.created_at.desc()).limit(50).all()
    
    return history
