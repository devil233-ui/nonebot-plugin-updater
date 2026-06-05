from __future__ import annotations

from typing import TYPE_CHECKING
from nonebot import get_driver, logger
from nonebot_plugin_updater.utils.models import PluginInfo

driver = get_driver()

class Updater:
    def __init__(
        self, plugin_update_list: list[PluginInfo], plugin_name: str | None = None
    ) -> None:
        self.plugin_update_list = plugin_update_list
        self.plugin_name = plugin_name

    @staticmethod
    def _run_with_auto_yes(cmd_list: list[str]) -> None:
        import pty
        import os
        import subprocess
        import threading
        import time

        master, slave = pty.openpty()
        try:
            # 伪装成终端运行，骗过交互式提示
            p = subprocess.Popen(cmd_list, stdin=slave, stdout=slave, stderr=slave)

            # 守护线程：实时将底层的 nbr 输出抽上来打印到控制台，拒绝摸黑！
            def drain():
                try:
                    while p.poll() is None:
                        data = os.read(master, 2048)
                        if data:
                            text = data.decode('utf-8', errors='ignore')
                            for line in text.split('\n'):
                                if line.strip():
                                    logger.info(f"[NBR] {line.strip()}")
                except OSError:
                    pass

            t = threading.Thread(target=drain, daemon=True)
            t.start()

            # 暴力循环输入：只要命令没结束，每 0.5 秒按一次 'y' 和回车
            # 彻底解决缓冲区被清空导致的卡死问题！
            while p.poll() is None:
                try:
                    os.write(master, b'y\n')
                except OSError:
                    pass
                time.sleep(0.5)

        except Exception as e:
            logger.error(f'执行命令出错 {cmd_list}: {e}')
        finally:
            os.close(slave)
            os.close(master)

    @staticmethod
    async def do_stop() -> None:
        import os
        logger.warning("执行强制断电退出...")
        os._exit(0)

    async def do_update(self) -> None:
        import os
        from shutil import which

        cli = which('nbr') or which('nb')
        if cli:
            logger.info(f'开始执行更新: {cli}')
            if self.plugin_name is not None:
                self._run_with_auto_yes([cli, 'plugin', 'update', self.plugin_name])
            else:
                for plugin in self.plugin_update_list:
                    self._run_with_auto_yes([cli, 'plugin', 'update', plugin.name])
        else:
            logger.error('未检测到 nbr 或 nb 指令！')

        logger.warning("更新完毕，执行强制断电重启...")
        os._exit(0)

    async def do_install(self) -> None:
        import os
        from shutil import which

        cli = which('nbr') or which('nb')
        if cli:
            logger.info(f'开始执行安装: {cli}')
            if self.plugin_name is not None:
                self._run_with_auto_yes([cli, 'plugin', 'install', self.plugin_name])
        else:
            logger.error('未检测到 nbr 或 nb 指令！')

        logger.warning("安装完毕，执行强制断电重启...")
        os._exit(0)

    async def do_uninstall(self) -> None:
        import os
        from shutil import which

        cli = which('nbr') or which('nb')
        if cli:
            logger.info(f'开始执行卸载: {cli}')
            if self.plugin_name is not None:
                self._run_with_auto_yes([cli, 'plugin', 'uninstall', self.plugin_name])
        else:
            logger.error('未检测到 nbr 或 nb 指令！')

        logger.warning("卸载完毕，执行强制断电重启...")
        os._exit(0)

    async def do_restart(self) -> None:
        import os
        logger.warning("收到重启指令，执行强制断电重启...")
        os._exit(0)