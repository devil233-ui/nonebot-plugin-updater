from __future__ import annotations

from pathlib import Path
from typing import Any

from nonebot import require
from nonebot.permission import SUPERUSER

from .config import plugin_config
from .utils.common import (
    get_plugin_info_list,
    get_plugin_module_list,
    get_plugin_update_list,
    get_store_plugins,
    plugin_info_text_builder,
    plugin_update_text_builder,
)
from .utils.models import NBPluginMetadata, PluginInfo
from .utils.updater import Updater

import json
import os
from nonebot.adapters import Bot, Event

def _save_restart_state(bot: Bot, event: Event, message: str) -> None:
    """保存重启前的信息到临时文件"""
    try:
        # 获取 OneBot V11 的事件信息
        session_id = event.get_session_id()
        is_group = session_id.startswith("group_")
        
        # 提取群号或私聊 QQ 号
        if is_group:
            target_id = session_id.split("_")[1]
        else:
            target_id = event.get_user_id()

        info = {
            'bot_id': bot.self_id,
            'is_group': is_group,
            'target_id': target_id,
            'message': message
        }
        
        with open('.restart_info.json', 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False)
    except Exception as e:
        from nonebot import logger
        logger.error(f"保存重启状态失败: {e}")
        
require('nonebot_plugin_alconna')
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaMatch,
    AlconnaMatcher,
    Args,
    Image,
    Match,
    Text,
    UniMessage,
    on_alconna,
)

_l: Alconna[Any] = Alconna('获取插件列表')
g_plugin_list: type[AlconnaMatcher] = on_alconna(_l, use_cmd_start=True)

_u: Alconna[Any] = Alconna('检查插件更新')
check_update: type[AlconnaMatcher] = on_alconna(_u, use_cmd_start=True)

_udr: Alconna[Any] = Alconna('更新插件', Args['plugin_name', str])
update_plugin: type[AlconnaMatcher] = on_alconna(
    _udr, use_cmd_start=True, permission=SUPERUSER
)

_idr: Alconna[Any] = Alconna('安装插件', Args['plugin_name', str])
install_plugin: type[AlconnaMatcher] = on_alconna(
    _idr, use_cmd_start=True, permission=SUPERUSER
)

_uidr: Alconna[Any] = Alconna('卸载插件', Args['plugin_name', str])
uninstall_plugin: type[AlconnaMatcher] = on_alconna(
    _uidr, use_cmd_start=True, permission=SUPERUSER
)

_c: Alconna[Any] = Alconna('关闭nb')
close_nb: type[AlconnaMatcher] = on_alconna(
    _c, use_cmd_start=True, permission=SUPERUSER
)

_r: Alconna[Any] = Alconna('重启nb')
restart_nb: type[AlconnaMatcher] = on_alconna(
    _r, use_cmd_start=True, permission=SUPERUSER
)


@g_plugin_list.handle()
async def _() -> None:
    plugin_module_list: list[str] = get_plugin_module_list()
    plugin_list: list[str] = []
    for moudle in plugin_module_list:
        plugin_list.append(moudle.replace('_', '-'))
    plugin_info_list: list[NBPluginMetadata] = await get_plugin_info_list(plugin_list)
    if plugin_config.info_send_mode == 'text':
        msg: UniMessage[Text] | UniMessage[Image] = UniMessage().text(
            plugin_info_text_builder(plugin_info_list)
        )
    else:
        from .utils.addition_for_htmlrender import template_element_to_pic

        template_path: Path = Path(__file__).parent / 'templates'
        img: bytes = await template_element_to_pic(
            str(template_path),
            template_name='plugin_info.jinja2',
            templates={'plugins': plugin_info_list},
            element='#container',
            wait=2,
        )
        msg = UniMessage().image(raw=img)
    await g_plugin_list.finish(msg)


@check_update.handle()
async def _() -> None:
    plugin_update_list: list[PluginInfo] = await get_plugin_update_list()
    if plugin_config.info_send_mode == 'text':
        msg: UniMessage[Text] | UniMessage[Image] = UniMessage().text(
            plugin_update_text_builder(plugin_update_list)
        )
    else:
        from .utils.addition_for_htmlrender import template_element_to_pic

        template_path: Path = Path(__file__).parent / 'templates'
        img: bytes = await template_element_to_pic(
            str(template_path),
            template_name='check_plugin_update.jinja2',
            templates={'plugins': plugin_update_list},
            element='#container',
            wait=2,
        )
        msg = UniMessage().image(raw=img)
    await check_update.finish(msg)


@update_plugin.handle()
async def _(
    bot: Bot, event: Event, plugin_name: Match[str] = AlconnaMatch('plugin_name')
) -> None:
    if plugin_name.available:
        plugin_update_list: list[PluginInfo] = await get_plugin_update_list()
        if plugin_name.result == 'all':
            if not plugin_update_list:
                await update_plugin.finish('所有插件已是最新')
            else:
                await update_plugin.send('正在更新插件中……')
                _save_restart_state(bot, event, '✨ 所有插件更新完成，重启成功！')
                updater: Updater = Updater(plugin_update_list)
                await updater.do_update()
        elif plugin_name.result in [plugin.name for plugin in plugin_update_list]:
            await update_plugin.send('正在更新插件中……')
            _save_restart_state(
                bot, event, f'✨ 插件 {plugin_name.result} 更新完成，重启成功！'
            )
            updater = Updater(plugin_update_list, plugin_name=plugin_name.result)
            await updater.do_update()
        else:
            await update_plugin.finish('无效的插件名/插件已是最新')


@install_plugin.handle()
async def _(
    bot: Bot, event: Event, plugin_name: Match[str] = AlconnaMatch('plugin_name')
) -> None:
    if plugin_name.available:
        store_plugins: list[NBPluginMetadata] = await get_store_plugins()
        if plugin_name.result in [plugin.project_link for plugin in store_plugins]:
            await install_plugin.send('正在安装插件中……')
            _save_restart_state(
                bot, event, f'✨ 插件 {plugin_name.result} 安装完成，重启成功！'
            )
            updater: Updater = Updater([], plugin_name.result)
            await updater.do_install()
        else:
            await install_plugin.finish('插件不存在')


@uninstall_plugin.handle()
async def _(
    bot: Bot, event: Event, plugin_name: Match[str] = AlconnaMatch('plugin_name')
) -> None:
    if plugin_name.available:
        store_plugins: list[NBPluginMetadata] = await get_store_plugins()
        if plugin_name.result in [plugin.project_link for plugin in store_plugins]:
            await uninstall_plugin.send('正在卸载插件中……')
            _save_restart_state(
                bot, event, f'✨ 插件 {plugin_name.result} 卸载完成，重启成功！'
            )
            updater: Updater = Updater([], plugin_name.result)
            await updater.do_uninstall()
        else:
            await uninstall_plugin.finish('插件不存在')


@close_nb.handle()
async def _() -> None:
    from nonebot import logger
    import os
    import sys

    logger.warning("收到关闭指令，正在执行强制断电...")
    # 发送终极无情退出信号，不管有没有后台任务，当场暴毙
    os._exit(0)


@restart_nb.handle()
async def _(bot: Bot, event: Event) -> None:
    await restart_nb.send('重启nb中……')
    _save_restart_state(bot, event, '✨ nb 重启成功！')
    await Updater([]).do_restart()
