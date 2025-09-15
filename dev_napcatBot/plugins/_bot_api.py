"""插件使用的集中化 `BotAPI` 单例模块。

本模块对外提供一个统一的 `api` 实例，插件可通过下面方式导入并使用：

        from dev_napcatBot.plugins._bot_api import api

设计目标：
- 在现代基于 asyncio 的应用中保持运行时行为简单明确；
- 将 `BotAPI` 的构造和任务调度集中管理，便于未来在单一位置修改调度或生命周期相关的逻辑；

说明与后续可扩展点：
- 当前实现假定存在一个正在运行的 asyncio 事件循环，直接使用
    ``asyncio.create_task`` 来调度后台协程。这种实现简单、轻量，适用于
    已经采用异步运行时（例如 FastAPI + uvicorn）的服务。
- 如果以后需要支持：
    - 优雅关闭（在退出时取消或等待未完成任务），
    - 每个任务的异常记录，或
    - 使用不同的调度器（线程池、外部 worker、或 `run_coroutine_threadsafe`），
    可以在此处扩展或替换 `_async_callback` 的实现。

示例：

        # 插件使用示例
        from dev_napcatBot.plugins._bot_api import api

        async def some_handler(...):
                # 使用 api 调用机器人动作
                await api.send_msg(...)

待办（可选改进）：
- 考虑添加任务跟踪（task-tracking）以便在应用关闭时取消或等待这些任务；
- 可选地通过环境变量配置调度策略，以支持开发模式下的兼容回退。

"""

import asyncio
from ncatbot.core.api import BotAPI


def _async_callback(coro):
        """使用当前事件循环将协程调度为后台任务。

        实现保持最小化：直接调用 ``asyncio.create_task``。若以后需要兼容
        在无事件循环或跨线程场景中运行，可在此处替换为使用
        ``asyncio.run_coroutine_threadsafe`` 的回退实现或更复杂的调度器。
        """
        return asyncio.create_task(coro)


# 插件可以直接导入并重用该单例
api = BotAPI(_async_callback)

