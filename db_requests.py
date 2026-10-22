from sqlalchemy import select
from database import async_session, User, InfoMessage
from tocentocen import OWNER_ID


# ---------- пользователи ----------

async def register_user(tg_id: int, username: str | None, name: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.username = username  # обновляем, если человек сменил ник или имя
            user.name = name
        else:
            session.add(User(tg_id=tg_id, username=username, name=name))
        await session.commit()



# ---------- баны ----------

async def is_banned(tg_id: int) -> bool:
    if tg_id == OWNER_ID:
        return False  # владельца забанить нельзя
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return bool(user and user.is_banned)



# ---------- информационные тексты (например, /help) ----------

async def get_info(key: str) -> str | None:
    async with async_session() as session:
        return await session.scalar(select(InfoMessage.text).where(InfoMessage.key == key))


async def set_info(key: str, text: str):
    async with async_session() as session:
        info = await session.scalar(select(InfoMessage).where(InfoMessage.key == key))
        if info:
            info.text = text
        else:
            session.add(InfoMessage(key=key, text=text))
        await session.commit()


# ---------- владелец ----------

async def ensure_owner():
    """Вызывается при старте: гарантирует, что владелец есть в базе как админ."""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == OWNER_ID))
        if user:
            user.is_admin = True
            user.is_banned = False
        else:
            session.add(User(tg_id=OWNER_ID, username=None, name='Владелец', is_admin=True))
        await session.commit()

async def is_admin(tg_id: int) -> bool:
    if tg_id == OWNER_ID:
        return True  # владелец всегда админ
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return bool(user and user.is_admin)


async def get_users() -> list[User]:
    """Обычные пользователи: не админы и не забаненные."""
    async with async_session() as session:
        return list((await session.scalars(
            select(User).where(User.is_admin == False, User.is_banned == False)
        )).all())


async def get_admins() -> list[User]:
    async with async_session() as session:
        return list((await session.scalars(
            select(User).where(User.is_admin == True)
        )).all())

async def get_user(tg_id: int) -> User | None:
    async with async_session() as session:
        return await session.scalar(select(User).where(User.tg_id == tg_id))


async def save_residence(tg_id: int, floor: int, section: str, room: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.floor = floor
            user.section = section
            user.room = room
            await session.commit()