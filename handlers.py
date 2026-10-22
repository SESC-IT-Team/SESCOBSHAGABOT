from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware, F, Router
from aiogram.filters import BaseFilter, Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from tocentocen import MAX_FLOOR 
import db_requests as rq

router = Router()

DEFAULT_HELP = (
    'Я бот с расписанием и информацией для общаги.\n\n'
    '/start - начать\n'
    '/help - справка\n'
    '/me - мои данные\n'
    '/reg - ввести этаж, отсек и комнату заново\n'
    '/cancel - отменить ввод'
)


class BanMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
                       event: Message, data: dict[str, Any]) -> Any:
        if event.from_user and await rq.is_banned(event.from_user.id):
            return  # забаненного игнорируем
        return await handler(event, data)


router.message.outer_middleware(BanMiddleware())


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return bool(message.from_user) and await rq.is_admin(message.from_user.id)


class Reg(StatesGroup):
    floor = State()
    section = State()
    room = State()


def where(p) -> str:
    if p.room is None:
        return 'не зарегистрирован'
    return f'этаж {p.floor}, отсек {p.section}, комната {p.room}'


def format_people(title: str, people) -> str:
    if not people:
        return f'{title}: список пуст'
    lines = [f'{title} ({len(people)}):']
    for i, p in enumerate(people, 1):
        nick = f'@{p.username}' if p.username else 'без ника'
        lines.append(f'{i}. {p.name} ({nick}), id {p.tg_id}, {where(p)}')
    return '\n'.join(lines)


async def send_long(message: Message, text: str):
    """Telegram не принимает сообщения длиннее 4096 символов, поэтому режем по строкам."""
    chunk = ''
    for line in text.split('\n'):
        if len(chunk) + len(line) + 1 > 4000:
            await message.answer(chunk)
            chunk = ''
        chunk += line + '\n'
    if chunk.strip():
        await message.answer(chunk)


async def ask_floor(message: Message, state: FSMContext):
    await state.set_state(Reg.floor)

    await message.answer(f'Введите номер этажа (число от 1 до {MAX_FLOOR}):')


# ---------- команды для всех ----------

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    u = message.from_user
    await rq.register_user(u.id, u.username, u.full_name)
    user = await rq.get_user(u.id)
    if user.room is None:
        await message.answer('Привет! Я бот с расписанием и информацией для общаги. '
                             'Сначала нужно зарегистрироваться.')
        await ask_floor(message, state)
    else:
        await message.answer(f'С возвращением! Вы зарегистрированы: {where(user)}.\n'
                             'Справка: /help')


@router.message(Command('help'))
async def help(message: Message):
    text = await rq.get_info('help')
    await message.answer(text or DEFAULT_HELP)


@router.message(Command('me'))
async def me(message: Message):
    user = await rq.get_user(message.from_user.id)
    if not user or user.room is None:
        return await message.answer('Вы ещё не зарегистрированы. Нажмите /reg')
    await message.answer(f'Ваши данные: {where(user)}.\nИзменить: /reg')


@router.message(Command('reg'))
async def reg(message: Message, state: FSMContext):
    u = message.from_user
    await rq.register_user(u.id, u.username, u.full_name)
    await ask_floor(message, state)


@router.message(Command('cancel'))
async def cancel(message: Message, state: FSMContext):
    if await state.get_state() is None:
        return await message.answer('Отменять нечего.')
    await state.clear()
    await message.answer('Ввод отменён. Зарегистрироваться можно командой /reg')


# ---------- регистрация по шагам ----------

@router.message(Reg.floor, F.text)
async def reg_floor(message: Message, state: FSMContext):
    t = message.text.strip()
    if not t.isdigit() or not 1 <= int(t) <= MAX_FLOOR:
        return await message.answer(f'Нужно число от 1 до {MAX_FLOOR}. Попробуйте ещё раз.')
    await state.update_data(floor=int(t))
    await state.set_state(Reg.section)
    await message.answer('Введите номер отсека:')


@router.message(Reg.section, F.text)
async def reg_section(message: Message, state: FSMContext):
    t = message.text.strip()
    if not t.isalnum() or len(t) > 10:
        return await message.answer('Отсек: до 10 символов, только цифры. Ещё раз:')
    await state.update_data(section=t.upper())
    await state.set_state(Reg.room)
    await message.answer('Введите номер комнаты:')


@router.message(Reg.room, F.text)
async def reg_room(message: Message, state: FSMContext):
    t = message.text.strip()
    if not t.isalnum() or len(t) > 10:
        return await message.answer('Комната: до 10 символов, только цифры. Ещё раз:')
    data = await state.get_data()
    await rq.save_residence(message.from_user.id, data['floor'], data['section'], t.upper())
    await state.clear()
    await message.answer(f'Готово! Вы зарегистрированы: этаж {data["floor"]}, '
                         f'отсек {data["section"]}, комната {t.upper()}.\n'
                         'Изменить данные можно командой /reg.')


@router.message(StateFilter(Reg))
async def reg_not_text(message: Message):
    await message.answer('Пожалуйста, отправьте ответ текстом. Отмена: /cancel')


# ---------- команды только для админов ----------

@router.message(Command('users'), IsAdmin())
async def users(message: Message):
    await send_long(message, format_people('Пользователи', await rq.get_users()))


@router.message(Command('admins'), IsAdmin())
async def admins(message: Message):
    await send_long(message, format_people('Админы', await rq.get_admins()))