from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from .models import UserRole, GameStatus, PropType

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    nickname: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    nickname: Optional[str]
    avatar_url: Optional[str]
    coins: int
    points: int
    role: UserRole
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class GameCreate(BaseModel):
    max_players: int = 6
    small_blind: int = 10
    big_blind: int = 20
    min_buy_in: int = 100

class JoinGameRequest(BaseModel):
    buy_in: int

class GameInfo(BaseModel):
    id: int
    room_id: str
    status: GameStatus
    max_players: int
    current_players: int
    small_blind: int
    big_blind: int
    min_buy_in: int
    pot: int
    community_cards: List
    current_round: str
    
    class Config:
        from_attributes = True

class PropUse(BaseModel):
    prop_type: PropType
    game_id: int
    target_player_id: Optional[int] = None

class BattleRecordResponse(BaseModel):
    id: int
    user_id: int
    game_id: int
    chips_start: int
    chips_end: int
    profit: int
    hole_cards: List
    community_cards: List
    final_hand: str
    is_winner: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class AdminUserUpdate(BaseModel):
    coins: Optional[int] = None
    points: Optional[int] = None
    win_rate_adjustment: Optional[float] = None
    is_active: Optional[bool] = None
