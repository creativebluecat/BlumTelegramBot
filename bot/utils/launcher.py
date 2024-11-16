import os
import glob
import asyncio
import json

from itertools import cycle
from typing import Tuple, List

from pyrogram import Client
from better_proxy import Proxy

from bot.config import settings
from bot.core.tapper import run_tapper
from bot.utils.logger import logger
from bot.utils.payload import check_payload_server

start_text = """
██████╗ ██╗     ██╗   ██╗███╗   ███╗████████╗ ██████╗ ██████╗  ██████╗ ████████╗
██╔══██╗██║     ██║   ██║████╗ ████║╚══██╔══╝██╔════╝ ██╔══██╗██╔═══██╗╚══██╔══╝
██████╔╝██║     ██║   ██║██╔████╔██║   ██║   ██║  ███╗██████╔╝██║   ██║   ██║   
██╔══██╗██║     ██║   ██║██║╚██╔╝██║   ██║   ██║   ██║██╔══██╗██║   ██║   ██║   
██████╔╝███████╗╚██████╔╝██║ ╚═╝ ██║   ██║   ╚██████╔╝██████╔╝╚██████╔╝   ██║   
╚═════╝ ╚══════╝ ╚═════╝ ╚═╝     ╚═╝   ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝    ╚═╝   
"""


def get_session_names() -> list[str]:
    session_names = sorted(glob.glob("sessions/*.session"))
    session_names = [
        os.path.splitext(os.path.basename(file))[0] for file in session_names
    ]

    return session_names





def get_tg_clients() -> dict[str, dict]:
    result: dict[str, dict] = {}
    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    file_path: str = 'sessions/accounts.json'
    with open(file_path, 'r') as f:
        accounts = json.load(f)

    for account in accounts:
        proxy = account.get('proxy', '')
        session_name = account.get('session_name', '')
        # 去除 ":@" 并转换为 socks5:// 格式
        if proxy.startswith(':@'):
            proxy = 'socks5://' + proxy[2:]
            proxy = Proxy.from_str(proxy)

        # 创建 Client 对象
        client = Client(
            name=session_name,
            api_id=settings.API_ID,
            api_hash=settings.API_HASH,
            workdir="sessions/",
            plugins=dict(root="bot/plugins"),
        )

        # 将 session_name、proxy 和 client 组合起来
        result[session_name] = {
            'proxy': proxy,
            'client': client
        }
        logger.info(f"load session:{session_name} proxy:{proxy} tg_client:{client}")
    return result

async def run_tasks():
    result = get_tg_clients()
    loop = asyncio.get_event_loop()

    if settings.USE_CUSTOM_PAYLOAD_SERVER and not await check_payload_server(settings.CUSTOM_PAYLOAD_SERVER_URL, full_test=True):
        logger.warning(
            f"The payload server on {settings.CUSTOM_PAYLOAD_SERVER_URL} is unavailable or not running. "
            f"<y>Without it, the bot will not play games for passes.</y> \n"
            f"<r>Read info</r>: https://github.com/HiddenCodeDevs/BlumTelegramBot/blob/main/PAYLOAD-SERVER.MD"
        )

    tasks = [
        loop.create_task(
            run_tapper(
                tg_client=config['client'],
                proxy=config['proxy']
            )
        )
        for config in  result.values()
    ]

    await asyncio.gather(*tasks)
