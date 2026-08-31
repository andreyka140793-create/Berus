"""REST API для Mini App Берусь!"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from models.entities import User, Order, Bid, Review
from services.auth_tg import validate_init_data
from config import CITIES, CATEGORIES
from services import notify as notify_svc
import asyncio

router = APIRouter(prefix="/api")


def current_user(
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    db: Session = Depends(get_db),
) -> User:
    data = validate_init_data(x_telegram_init_data or "")
    if not data or "id" not in data:
        raise HTTPException(401, "Unauthorized")
    tid = int(data["id"])
    user = db.query(User).filter(User.telegram_id == tid).one_or_none()
    if user is None:
        user = User(
            telegram_id=tid,
            username=data.get("username"),
            full_name=(data.get("first_name") or "") + (" " + data["last_name"] if data.get("last_name") else ""),
            role="customer",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    if user.is_blocked:
        raise HTTPException(403, "Blocked")
    return user


@router.get("/meta")
def meta():
    return {"cities": CITIES, "categories": CATEGORIES, "name": "Берусь!"}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "city_slug": user.city_slug,
        "bio": user.bio,
        "categories": (user.categories or "").split(",") if user.categories else [],
        "rating": user.rating,
        "rating_count": user.rating_count,
    }


class ProfileIn(BaseModel):
    role: str | None = None
    city_slug: str | None = None
    bio: str | None = None
    categories: list[str] | None = None
    phone: str | None = None


@router.patch("/me")
def update_me(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.role in ("customer", "performer", "both"):
        user.role = body.role
    if body.city_slug is not None:
        user.city_slug = body.city_slug
    if body.bio is not None:
        user.bio = body.bio
    if body.categories is not None:
        user.categories = ",".join(body.categories)
    if body.phone is not None:
        user.phone = body.phone
    db.commit()
    return {"ok": True}


class OrderIn(BaseModel):
    city_slug: str
    category_slug: str
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=4000)
    budget: int | None = None


@router.post("/orders")
async def create_order(body: OrderIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = Order(
        customer_id=user.id,
        city_slug=body.city_slug,
        category_slug=body.category_slug,
        title=body.title.strip(),
        description=body.description.strip(),
        budget=body.budget,
        status="open",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # уведомления исполнителям города (не заказчику)
    performers = (
        db.query(User)
        .filter(
            User.is_blocked.is_(False),
            User.role.in_(("performer", "both")),
            User.city_slug == order.city_slug,
            User.id != user.id,
        )
        .all()
    )
    # если у исполнителя не указан город — тоже можно слать по желанию; пока только совпадение города
    ids = [p.telegram_id for p in performers]
    if ids:
        await notify_svc.notify_new_order(order, ids)

    return {"id": order.id, "notified_performers": len(ids)}


@router.get("/orders")
def list_orders(
    city_slug: str | None = None,
    category_slug: str | None = None,
    status: str = "open",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Order).filter(Order.status == status)
    if city_slug:
        q = q.filter(Order.city_slug == city_slug)
    if category_slug:
        q = q.filter(Order.category_slug == category_slug)
    rows = q.order_by(Order.created_at.desc()).limit(50).all()
    return [
        {
            "id": o.id,
            "city_slug": o.city_slug,
            "category_slug": o.category_slug,
            "title": o.title,
            "description": o.description,
            "budget": o.budget,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "bids_count": len(o.bids),
        }
        for o in rows
    ]


@router.get("/orders/{order_id}")
def get_order(order_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).one_or_none()
    if not o:
        raise HTTPException(404, "Not found")
    return {
        "id": o.id,
        "city_slug": o.city_slug,
        "category_slug": o.category_slug,
        "title": o.title,
        "description": o.description,
        "budget": o.budget,
        "status": o.status,
        "customer_telegram_id": o.customer.telegram_id if o.customer else None,
        "bids": [
            {
                "id": b.id,
                "message": b.message,
                "price": b.price,
                "status": b.status,
                "performer": {
                    "telegram_id": b.performer.telegram_id,
                    "username": b.performer.username,
                    "full_name": b.performer.full_name,
                    "rating": b.performer.rating,
                },
            }
            for b in o.bids
        ],
    }


class BidIn(BaseModel):
    message: str = Field(min_length=3, max_length=2000)
    price: int | None = None


@router.post("/orders/{order_id}/bids")
async def create_bid(
    order_id: int,
    body: BidIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role not in ("performer", "both"):
        raise HTTPException(400, "Сначала укажите роль исполнителя в профиле")
    o = db.query(Order).filter(Order.id == order_id, Order.status == "open").one_or_none()
    if not o:
        raise HTTPException(404, "Заявка не найдена или закрыта")
    if o.customer_id == user.id:
        raise HTTPException(400, "Нельзя откликаться на свою заявку")
    exists = (
        db.query(Bid)
        .filter(Bid.order_id == order_id, Bid.performer_id == user.id)
        .one_or_none()
    )
    if exists:
        raise HTTPException(400, "Вы уже откликались")
    # простой антиспам: не больше 20 откликов в сутки
    from datetime import datetime, timedelta
    day_ago = datetime.utcnow() - timedelta(days=1)
    cnt = db.query(Bid).filter(Bid.performer_id == user.id, Bid.created_at >= day_ago).count()
    if cnt >= 20:
        raise HTTPException(429, "Лимит откликов на сегодня (20)")
    bid = Bid(
        order_id=order_id,
        performer_id=user.id,
        message=body.message.strip(),
        price=body.price,
        status="sent",
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)

    # уведомление заказчику
    customer = o.customer
    if customer and customer.telegram_id:
        pname = user.full_name or (("@%s" % user.username) if user.username else "Исполнитель")
        await notify_svc.notify_new_bid(
            customer.telegram_id,
            o.title,
            pname,
            bid.message,
            bid.price,
        )

    return {"id": bid.id, "free": True}


@router.get("/my/orders")
def my_orders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Order)
        .filter(Order.customer_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(50)
        .all()
    )
    return [{"id": o.id, "title": o.title, "status": o.status, "bids_count": len(o.bids)} for o in rows]


@router.get("/my/bids")
def my_bids(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Bid)
        .filter(Bid.performer_id == user.id)
        .order_by(Bid.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": b.id,
            "order_id": b.order_id,
            "order_title": b.order.title if b.order else None,
            "status": b.status,
            "message": b.message,
        }
        for b in rows
    ]


class ReviewIn(BaseModel):
    order_id: int
    to_telegram_id: int
    score: int = Field(ge=1, le=5)
    text: str | None = None


@router.post("/reviews")
def add_review(body: ReviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    to_user = db.query(User).filter(User.telegram_id == body.to_telegram_id).one_or_none()
    if not to_user:
        raise HTTPException(404, "Пользователь не найден")
    rev = Review(
        order_id=body.order_id,
        from_user_id=user.id,
        to_user_id=to_user.id,
        score=body.score,
        text=(body.text or "").strip() or None,
    )
    db.add(rev)
    to_user.rating_sum = (to_user.rating_sum or 0) + body.score
    to_user.rating_count = (to_user.rating_count or 0) + 1
    db.commit()
    return {"ok": True}
