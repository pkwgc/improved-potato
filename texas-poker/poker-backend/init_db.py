from app.database import engine, Base
from app.models import User, Game, GamePlayer, BattleRecord, PropUsage, Club, DailyTask
from app.auth import get_password_hash
from sqlalchemy.orm import Session

def init_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
    
    with Session(engine) as session:
        admin_user = session.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("Creating default admin user...")
            admin_user = User(
                username="admin",
                email="admin@texaspoker.com",
                hashed_password=get_password_hash("admin123"),
                nickname="Admin",
                coins=10000,
                role="admin"
            )
            session.add(admin_user)
            session.commit()
            print("Admin user created! Username: admin, Password: admin123")
        else:
            print("Admin user already exists")
        
        test_user = session.query(User).filter(User.username == "testuser").first()
        if not test_user:
            print("Creating test user...")
            test_user = User(
                username="testuser",
                email="test@texaspoker.com",
                hashed_password=get_password_hash("test123"),
                nickname="Test Player",
                coins=5000
            )
            session.add(test_user)
            session.commit()
            print("Test user created! Username: testuser, Password: test123")
        else:
            print("Test user already exists")

if __name__ == "__main__":
    init_database()
