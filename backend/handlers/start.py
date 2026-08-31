""" /start и базовые команды """
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from database import SessionLocal
from models.entities import User
from keyboards.main import main_kb, webapp_kb

router = Router()


def upsert_user(message: Message) -> dict:
    u = message.from_user
    with SessionLocal() as db:
        user = db.query(User).filter(User.telegram_id == u.id).one_or_none()
        if user is None:
            user = User(
                telegram_id=u.id,
                username=u.username,
                full_name=u.full_name,
                role="customer",
            )
            db.add(user)
        else:
            user.username = u.username
            user.full_name = u.full_name
        db.commit()
        db.refresh(user)
        return {
            "telegram_id": user.telegram_id,
            "role": user.role,
            "city_slug": user.city_slug,
            "rating": user.rating,
            "rating_count": user.rating_count,
        }


@router.message(CommandStart())
async def cmd_start(message: Message):
    upsert_user(message)
    text = (
        "👋 Это *Берусь!* — заявки на услуги в Telegram.\n\n"
        "Заказчик создаёт задачу.\n"
        "Исполнитель *бесплатно* откликается.\n\n"
        "Откройте приложение кнопкой ниже."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_kb())
    await message.answer("Мини-приложение:", reply_markup=webapp_kb())


@router.message(Command("help"))
@router.message(F.text.in_({"❓ Помощь", "Помощь"}))
async def cmd_help(message: Message):
    await message.answer(
        "Как пользоваться Берусь!\n\n"
        "1. Откройте мини-приложение\n"
        "2. Выберите роль: заказчик или исполнитель\n"
        "3. Заказчик создаёт заявку по городу и категории\n"
        "4. Исполнитель видит ленту и откликается бесплатно\n"
        "5. Договоритесь в Telegram и оставьте отзыв\n\n"
        "Поддержка: /support"
    )


@router.message(F.text.in_({"📱 Открыть Берусь!", "Открыть Берусь!"}))
async def open_app(message: Message):
    await message.answer("Откройте приложение:", reply_markup=webapp_kb())


@router.message(F.text.in_({"👤 Профиль", "Профиль"}))
async def profile(message: Message):
    data = upsert_user(message)
    await message.answer(
        "Профиль\n"
        f"ID: {data['telegram_id']}\n"
        f"Роль: {data['role']}\n"
        f"Город: {data['city_slug'] or '—'}\n"
        f"Рейтинг: {data['rating']} ({data['rating_count']})"
    )
