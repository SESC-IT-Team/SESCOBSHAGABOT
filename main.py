import asyncio
import logging
import uvicorn
from aiogram import Bot, Dispatcher
from handlers import router
from tocentocen import tocen
from database import init_db
from web_admin import create_app
import db_requests as rq

logging.basicConfig(level=logging.INFO)


async def main():
    await init_db()
    await rq.ensure_owner()

    bot = Bot(token=tocen)
    dp = Dispatcher()
    dp.include_router(router)

    server = uvicorn.Server(uvicorn.Config(create_app(), host='127.0.0.1', port=8000))
    await asyncio.gather(dp.start_polling(bot), server.serve())


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('бот выключен')