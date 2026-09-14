from uuid import UUID

from sqlalchemy import delete, select

from app.db.models.memory import MemoryDB


class MemoryRepository:

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def create(
        self,
        memory: MemoryDB,
    ) -> MemoryDB:

        with self.session_factory() as session:

            session.add(memory)
            session.commit()
            session.refresh(memory)

            return memory

    def get(
        self,
        memory_id: UUID,
    ) -> MemoryDB | None:

        with self.session_factory() as session:

            return session.scalar(
                select(MemoryDB).where(
                    MemoryDB.id == memory_id
                )
            )

    def list_by_user(
        self,
        user_id: UUID,
    ) -> list[MemoryDB]:

        with self.session_factory() as session:

            return list(
                session.scalars(
                    select(MemoryDB)
                    .where(
                        MemoryDB.user_id == user_id
                    )
                    .order_by(
                        MemoryDB.created_at.desc()
                    )
                )
            )

    def delete(
        self,
        memory_id: UUID,
    ) -> bool:

        with self.session_factory() as session:

            result = session.execute(
                delete(MemoryDB).where(
                    MemoryDB.id == memory_id
                )
            )

            session.commit()

            return result.rowcount == 1

    def find_by_content(
        self,
        user_id: UUID,
        content: str,
    ) -> MemoryDB | None:

        with self.session_factory() as session:

            return session.scalar(
                select(MemoryDB)
                .where(
                    MemoryDB.user_id == user_id,
                    MemoryDB.content == content,
                )
            )