from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from database import engine, User, InfoMessage
from tocentocen import ADMIN_LOGIN, ADMIN_PASSWORD, SECRET_KEY, OWNER_ID


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        if form.get('username') == ADMIN_LOGIN and form.get('password') == ADMIN_PASSWORD:
            request.session.update({'token': 'ok'})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get('token') == 'ok'


class UserAdmin(ModelView, model=User):
    name = 'Пользователь'
    name_plural = 'Пользователи'
    column_list = [User.id, User.tg_id, User.username, User.name, User.floor, User.section, User.room, User.is_admin, User.is_banned]
    column_searchable_list = [User.username, User.name, User.room]
    column_sortable_list = [User.id, User.is_admin, User.is_banned]
    form_columns = [User.username, User.name, User.floor, User.section, User.room, User.is_admin, User.is_banned]
    can_create = False
    can_delete = False

    async def on_model_change(self, data, model, is_created, request):
        # защита владельца: права и бан менять нельзя
        if model is not None and model.tg_id == OWNER_ID:
            data['is_admin'] = True
            data['is_banned'] = False


class InfoAdmin(ModelView, model=InfoMessage):
    name = 'Текст'
    name_plural = 'Тексты (help и др.)'
    column_list = [InfoMessage.id, InfoMessage.key, InfoMessage.text]


def create_app() -> FastAPI:
    app = FastAPI()
    admin = Admin(app, engine, authentication_backend=AdminAuth(secret_key=SECRET_KEY))
    admin.add_view(UserAdmin)
    admin.add_view(InfoAdmin)
    return app