from alembic import context

from backend.config import settings
from backend.database import Base, make_engine
from backend import models  # noqa: F401

target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = make_engine(settings.database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
