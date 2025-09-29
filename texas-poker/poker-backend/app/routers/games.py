from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import json
import uuid
from .. import models, schemas, auth
from ..database import get_db
from ..game_manager import game_manager, PokerGame

router = APIRouter(prefix="/api/games", tags=["games"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: int):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        self.active_connections[game_id].append(websocket)

    def disconnect(self, websocket: WebSocket, game_id: int):
        if game_id in self.active_connections:
            self.active_connections[game_id].remove(websocket)

    async def broadcast(self, message: dict, game_id: int):
        if game_id in self.active_connections:
            for connection in self.active_connections[game_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@router.post("/create", response_model=schemas.GameInfo)
def create_game(
    game_create: schemas.GameCreate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    room_id = str(uuid.uuid4())[:8]
    
    game = models.Game(
        room_id=room_id,
        max_players=game_create.max_players,
        small_blind=game_create.small_blind,
        big_blind=game_create.big_blind,
        min_buy_in=game_create.min_buy_in,
        status=models.GameStatus.WAITING
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    
    return game

@router.get("/list", response_model=List[schemas.GameInfo])
def list_games(
    status: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    query = db.query(models.Game)
    if status:
        query = query.filter(models.Game.status == status)
    games = query.order_by(models.Game.created_at.desc()).limit(50).all()
    return games

@router.post("/join/{game_id}")
def join_game(
    game_id: int,
    join_request: schemas.JoinGameRequest,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game.status != models.GameStatus.WAITING:
        raise HTTPException(status_code=400, detail="Game already started")
    
    if game.current_players >= game.max_players:
        raise HTTPException(status_code=400, detail="Game is full")
    
    buy_in = join_request.buy_in
    if buy_in < game.min_buy_in:
        raise HTTPException(status_code=400, detail=f"Minimum buy-in is {game.min_buy_in}")
    
    if current_user.coins < buy_in:
        raise HTTPException(status_code=400, detail="Insufficient coins")
    
    existing_player = db.query(models.GamePlayer).filter(
        models.GamePlayer.game_id == game_id,
        models.GamePlayer.user_id == current_user.id
    ).first()
    if existing_player:
        raise HTTPException(status_code=400, detail="Already joined this game")
    
    current_user.coins -= buy_in
    
    game_player = models.GamePlayer(
        game_id=game_id,
        user_id=current_user.id,
        position=game.current_players,
        chips=buy_in
    )
    db.add(game_player)
    
    game.current_players += 1
    
    db.commit()
    
    return {"success": True, "position": game_player.position}

@router.post("/start/{game_id}")
def start_game(
    game_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game.status != models.GameStatus.WAITING:
        raise HTTPException(status_code=400, detail="Game already started")
    
    if game.current_players < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players")
    
    poker_game = game_manager.create_game(game_id, db)
    poker_game.load_from_db()
    poker_game.start_game()
    
    game.status = models.GameStatus.PLAYING
    game.started_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}

@router.post("/action/{game_id}")
def player_action(
    game_id: int,
    action: str,
    amount: int = 0,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    player = db.query(models.GamePlayer).filter(
        models.GamePlayer.game_id == game_id,
        models.GamePlayer.user_id == current_user.id
    ).first()
    if not player:
        raise HTTPException(status_code=400, detail="Not in this game")
    
    poker_game = game_manager.get_game(game_id)
    if not poker_game:
        poker_game = game_manager.create_game(game_id, db)
        poker_game.load_from_db()
    
    result = poker_game.player_action(player.position, action, amount)
    
    return result

@router.get("/{game_id}", response_model=schemas.GameInfo)
def get_game(
    game_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

@router.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: int, db: Session = Depends(get_db)):
    await manager.connect(websocket, game_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            await manager.broadcast({
                "type": "game_update",
                "data": message
            }, game_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)
