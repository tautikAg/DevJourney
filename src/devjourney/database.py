"""
Database setup and configuration for the DevJourney application.

This module handles database initialization, connection management,
and provides utility functions for database operations.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Type, TypeVar

from sqlmodel import Session, SQLModel, create_engine, select

from devjourney.models import AppConfig, Conversation, DailyLog, Insight, Message, SyncStatus

T = TypeVar("T", bound=SQLModel)

# Default database path
DEFAULT_DB_PATH = Path("./data/devjourney.db")


class Database:
    """Database manager for the DevJourney application."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file. If None, uses the default path.
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_data_dir()
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        self._create_tables()
        self._initialize_default_config()

    def _ensure_data_dir(self) -> None:
        """Ensure the data directory exists."""
        data_dir = self.db_path.parent
        data_dir.mkdir(parents=True, exist_ok=True)

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        SQLModel.metadata.create_all(self.engine)

    def _initialize_default_config(self) -> None:
        """Initialize default configuration if it doesn't exist."""
        with self.session() as session:
            config = session.exec(select(AppConfig)).first()
            if not config:
                default_config = AppConfig()
                session.add(default_config)
                session.commit()

            # Initialize sync status for each component
            components = ["extraction", "analysis", "notion_sync"]
            for component in components:
                sync_status = session.exec(
                    select(SyncStatus).where(SyncStatus.component == component)
                ).first()
                if not sync_status:
                    default_status = SyncStatus(component=component)
                    session.add(default_status)
                    session.commit()

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Create a database session context manager.
        
        Yields:
            A SQLModel session that will be automatically closed when the context exits.
        """
        session = Session(self.engine)
        try:
            yield session
        finally:
            session.close()

    def get_config(self) -> AppConfig:
        """Get the application configuration.
        
        Returns:
            The application configuration.
        """
        with self.session() as session:
            config = session.exec(select(AppConfig)).first()
            if not config:
                config = AppConfig()
                session.add(config)
                session.commit()
            return config

    def update_config(self, **kwargs: Any) -> AppConfig:
        """Update the application configuration.
        
        Args:
            **kwargs: Configuration parameters to update.
            
        Returns:
            The updated application configuration.
        """
        with self.session() as session:
            config = session.exec(select(AppConfig)).first()
            if not config:
                config = AppConfig(**kwargs)
                session.add(config)
            else:
                for key, value in kwargs.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            session.commit()
            session.refresh(config)
            return config

    def update_config_object(self, config: AppConfig) -> AppConfig:
        """Update the application configuration with a config object.
        
        Args:
            config: The AppConfig object to update with.
            
        Returns:
            The updated application configuration.
        """
        with self.session() as session:
            existing_config = session.exec(select(AppConfig)).first()
            if not existing_config:
                session.add(config)
            else:
                # Update the existing config with values from the provided config
                for key, value in config.dict().items():
                    if hasattr(existing_config, key):
                        setattr(existing_config, key, value)
                config = existing_config
            session.commit()
            session.refresh(config)
            return config

    def get_sync_status(self) -> SyncStatus:
        """Get the sync status.
        
        Returns:
            The sync status.
        """
        with self.session() as session:
            status = session.exec(select(SyncStatus)).first()
            if not status:
                status = SyncStatus()
                session.add(status)
                session.commit()
            return status

    def update_sync_status(self, **kwargs: Any) -> SyncStatus:
        """Update the sync status.
        
        Args:
            **kwargs: Status parameters to update.
            
        Returns:
            The updated sync status.
        """
        with self.session() as session:
            status = session.exec(select(SyncStatus)).first()
            if not status:
                status = SyncStatus(**kwargs)
                session.add(status)
            else:
                for key, value in kwargs.items():
                    if hasattr(status, key):
                        setattr(status, key, value)
            session.commit()
            session.refresh(status)
            return status

    def add_item(self, item: SQLModel) -> SQLModel:
        """Add an item to the database.
        
        Args:
            item: The item to add.
            
        Returns:
            The added item with its ID set.
        """
        with self.session() as session:
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def add_items(self, items: List[SQLModel]) -> List[SQLModel]:
        """Add multiple items to the database.
        
        Args:
            items: The items to add.
            
        Returns:
            The added items with their IDs set.
        """
        with self.session() as session:
            for item in items:
                session.add(item)
            session.commit()
            for item in items:
                session.refresh(item)
            return items

    def get_item(self, model_class: Type[T], item_id: int) -> Optional[T]:
        """Get an item by ID.
        
        Args:
            model_class: The model class.
            item_id: The item ID.
            
        Returns:
            The item, or None if not found.
        """
        with self.session() as session:
            return session.get(model_class, item_id)

    def get_items(self, model_class: Type[T], **filters: Any) -> List[T]:
        """Get items with optional filters.
        
        Args:
            model_class: The model class.
            **filters: Optional filters to apply.
            
        Returns:
            A list of matching items.
        """
        with self.session() as session:
            query = select(model_class)
            for attr, value in filters.items():
                if hasattr(model_class, attr):
                    query = query.where(getattr(model_class, attr) == value)
            return list(session.exec(query))

    def update_item(self, item: SQLModel) -> SQLModel:
        """Update an item in the database.
        
        Args:
            item: The item to update.
            
        Returns:
            The updated item.
        """
        with self.session() as session:
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def delete_item(self, item: SQLModel) -> None:
        """Delete an item from the database.
        
        Args:
            item: The item to delete.
        """
        with self.session() as session:
            session.delete(item)
            session.commit()


# Global database instance
db = Database()


def get_db() -> Database:
    """Get the global database instance.
    
    Returns:
        The global database instance.
    """
    return db

def init_db() -> None:
    """Initialize the database."""
    db = get_db()
    # The database is initialized when the Database instance is created
