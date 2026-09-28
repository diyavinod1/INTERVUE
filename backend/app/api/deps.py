from app.db.session import get_db  # re-exported so routes import everything from app.api.deps

__all__ = ["get_db"]
