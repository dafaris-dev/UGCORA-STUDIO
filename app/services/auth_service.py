"""Private single-owner authentication."""
import os
import logging
import bcrypt
from sqlalchemy.orm import Session
from app.models.user import User

logger = logging.getLogger(__name__)


def hash_password(plain: str) -> str:
    # bcrypt limits input to 72 bytes
    secret = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(secret, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        secret = plain.encode("utf-8")[:72]
        return bcrypt.checkpw(secret, hashed.encode("utf-8"))
    except Exception:
        return False


def ensure_admin_user(db: Session) -> User:
    """Create or sync the single admin user from env on startup."""
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "change-me-now")

    user = db.query(User).filter(User.username == username).one_or_none()
    if user is None:
        db.query(User).delete()
        user = User(username=username, password_hash=hash_password(password))
        db.add(user)
        db.commit()
        logger.info("Admin user created: %s", username)
    else:
        if not verify_password(password, user.password_hash):
            user.password_hash = hash_password(password)
            db.commit()
            logger.info("Admin password synced from env.")
    return user


def authenticate(db: Session, username: str, password: str) -> bool:
    user = db.query(User).filter(User.username == username).one_or_none()
    if not user:
        return False
    return verify_password(password, user.password_hash)
