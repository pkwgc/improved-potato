# Texas Poker App

A full-stack Texas Hold'em poker application with real-time gameplay, prop system, and admin panel.

## Project Structure

```
texas-poker/
├── poker-backend/     # FastAPI backend with WebSocket support
└── poker-frontend/    # React + TypeScript frontend
```

## Backend

### Technology Stack
- **Framework**: FastAPI
- **Database**: PostgreSQL (configurable via DATABASE_URL)
- **Authentication**: JWT tokens
- **Real-time**: WebSocket
- **ORM**: SQLAlchemy

### Local Development with PostgreSQL

A local PostgreSQL database has been set up for development:

```bash
# Database credentials (local only)
Database: poker_db
User: poker_user
Password: poker_password_change_in_production
Host: localhost:5432
```

To run the backend locally:

```bash
cd poker-backend

# Install dependencies
poetry install

# Update .env to use PostgreSQL
DATABASE_URL=postgresql+psycopg://poker_user:poker_password_change_in_production@localhost:5432/poker_db

# Initialize database (creates tables and seed data)
poetry run python init_db.py

# Start development server
poetry run fastapi dev app/main.py
```

Default test accounts:
- Admin: `admin` / `admin123`
- Test user: `testuser` / `test123`

### Production Deployment

The backend is deployed at: **https://app-ydsmpbvb.fly.dev/**

#### Switching to Production PostgreSQL

To connect the deployed backend to your own PostgreSQL database:

1. Set the DATABASE_URL environment variable on Fly.io:
   ```bash
   flyctl secrets set DATABASE_URL="postgresql+psycopg://user:password@your-host:5432/your_database"
   ```

2. Scale to multiple instances (optional, after PostgreSQL is configured):
   ```bash
   flyctl scale count 2
   ```

The DATABASE_URL format:
```
postgresql+psycopg://username:password@host:port/database_name
```

For example with Aliyun/Tencent Cloud PostgreSQL:
```
postgresql+psycopg://poker_user:secure_password@rm-xxxxx.postgres.rds.aliyuncs.com:5432/poker_production
```

**Important**: The current deployment uses SQLite with a single instance for testing purposes. SQLite data is ephemeral and will be lost on restart. You MUST configure PostgreSQL for production use.

### API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs` (local) or `https://app-ydsmpbvb.fly.dev/docs` (production)
- ReDoc: `http://localhost:8000/redoc`

### Key Features

#### Authentication
- POST `/api/auth/register` - Register new user
- POST `/api/auth/login` - Login (returns JWT token)
- GET `/api/auth/me` - Get current user info
- PUT `/api/auth/me` - Update user profile

#### Game Management
- GET `/api/games/list` - List available games
- POST `/api/games/create` - Create new game room
- POST `/api/games/join/{game_id}` - Join a game
- POST `/api/games/start/{game_id}` - Start game
- POST `/api/games/action/{game_id}` - Player action (fold/call/raise)
- WS `/api/games/ws/{game_id}` - Real-time game updates

#### Props System
- POST `/api/props/use` - Use prop (view opponent cards / future cards)
- GET `/api/props/history` - View prop usage history

#### Profile
- GET `/api/profile/battle-records` - Get battle history (90 days retention)
- GET `/api/profile/statistics` - User statistics
- POST `/api/profile/daily-signin` - Daily sign-in for coins

#### Admin Panel
- GET `/api/admin/users` - List all users
- PUT `/api/admin/users/{user_id}` - Update user (coins, win rate adjustment)
- GET `/api/admin/statistics` - Platform statistics
- GET `/api/admin/prop-usage` - Prop usage analytics

## Frontend

### Technology Stack
- **Framework**: React + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **Icons**: Lucide React
- **Routing**: React Router

### Local Development

```bash
cd poker-frontend

# Install dependencies
npm install

# Update .env with backend URL
VITE_API_URL=http://localhost:8000

# Start development server
npm run dev
```

Visit http://localhost:5173

### Production Deployment

The frontend is deployed at: **https://texas-poker-app-coox1oen.devinapps.com**

To redeploy:
```bash
cd poker-frontend

# Update .env with production backend URL
VITE_API_URL=https://app-ydsmpbvb.fly.dev

# Build
npm run build

# Deploy (requires Devin deployment tools)
# This will be handled by the deployment system
```

### Features

1. **User Authentication**
   - Registration with email validation
   - Secure login with JWT
   - Profile management

2. **Game Lobby**
   - Browse available games
   - Filter by status and player count
   - Quick match feature
   - Create custom rooms

3. **Texas Hold'em Gameplay**
   - Standard poker rules
   - 2-9 players per table
   - Real-time card dealing animations
   - Betting actions: fold, call, raise, check
   - Pot calculation and winner determination

4. **Props System** (付费道具)
   - **View Opponent Cards** (看其他人的牌): 100 coins, once per game
   - **View Future Cards** (看后面的牌): 150 coins, up to 2 times per game
   - Confirmation dialogs before purchase
   - Real-time updates via WebSocket

5. **Battle Records**
   - View last 50 games
   - Win/loss statistics
   - Hand history with community cards
   - Prop usage tracking

6. **Admin Panel**
   - User management (ban, adjust coins)
   - Win rate adjustment per user/room
   - Platform analytics
   - Prop revenue tracking

## Data Retention

- Battle records: **90 days** (configurable in backend)
- User data: Permanent
- Game sessions: Cleared after completion
- Prop usage logs: Permanent for analytics

## Security

- JWT authentication with secure secret key
- Password hashing with bcrypt
- HTTPS enforced in production
- CORS configured for frontend domain
- Input validation on all endpoints
- Rate limiting (recommended for production)

## Database Schema

Key tables:
- `users` - User accounts and profiles
- `games` - Game sessions and state
- `players` - Player positions in games
- `battle_records` - Game history for each player
- `prop_usage` - Prop purchase and usage logs
- `daily_signin` - Daily sign-in tracking

## Next Steps

1. **Configure Production Database**
   - Set up managed PostgreSQL (Aliyun RDS / Tencent Cloud)
   - Update Fly.io DATABASE_URL secret
   - Run database migrations

2. **Mobile App Development**
   - Use same backend API
   - Implement with Flutter or React Native
   - Share WebSocket game logic

3. **Additional Features**
   - WeChat/QQ social login
   - Voice chat integration
   - Tournament mode
   - Club system with rankings
   - Push notifications

4. **Production Readiness**
   - Set up monitoring (e.g., Sentry)
   - Configure backups for PostgreSQL
   - Add rate limiting
   - Set up CDN for frontend assets
   - Implement proper logging

## Support

For questions or issues, contact the development team.
