# Texas Poker Backend

FastAPI backend for Texas Hold'em Poker game with real-time gameplay, props system, and admin panel.

## Features

- User authentication and profile management
- Real-time Texas Hold'em poker gameplay (2-9 players)
- Props system: View other players' cards, View future cards
- Admin panel: User management, win rate adjustment, statistics
- Battle records with 90-day retention
- WebSocket support for real-time game updates

## Setup

1. Install dependencies:
```bash
poetry install
```

2. Configure environment variables in `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/poker_db
SECRET_KEY=your-secret-key
```

3. Initialize database:
```bash
poetry run python init_db.py
```

4. Run development server:
```bash
poetry run fastapi dev app/main.py
```

## API Endpoints

- `/docs` - Interactive API documentation
- `/api/auth/*` - Authentication endpoints
- `/api/games/*` - Game management endpoints
- `/api/props/*` - Props usage endpoints
- `/api/admin/*` - Admin panel endpoints
- `/api/profile/*` - User profile endpoints

## Default Credentials

- Admin: username=`admin`, password=`admin123`
- Test User: username=`testuser`, password=`test123`

## Deployment

Deploy using the deploy_backend command.
