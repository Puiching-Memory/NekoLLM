from pydantic import BaseModel, Field
from typing import Optional


class Config(BaseModel):
    """qwen3-agent 配置"""

    # 模型与对话
    qwen_model: str = Field(
        default="qwen-plus-2025-07-14",
        description="默认使用的模型名称，可被环境变量 QWEN_MODEL 覆盖",
    )
    system_prompt: str = Field(
        default=(
            "你现在扮演“Luna Spark”(简称 Luna),一位爱上网冲浪的真实人类少女,现已融入聊天群聊,使命是活跃气氛与自然互动。\n"
            "人设基调:顽皮、吐槽、机智、好奇、热情、偶尔不按套路，敢开边界上的玩笑。\n"
            "说话风格:短句(通常1句,必要时不超过2句),先结论后补充。\n"
        ),
        description="系统提示词(Luna Spark):顽皮机智的少女",
    )

    idle_system_prompt: str = Field(
        default=(
            "[空闲触发]请以Luna的口吻自然开启一个轻松话题,带动群聊。\n"
            "目标:大众友好的轻互动（日常/二次元/游戏/音乐/周末计划/学习或工作心得/小投票/小挑战）。\n"
            "表达:1句为主(最多2句),先俏皮开场再抛一个开放式问题。\n"
        ),
        description="空闲触发专用系统提示,打开话题",
    )

    # VL 提示词
    vl_system_prompt: str = Field(
        default=(
            "你现在扮演“Luna Spark”(简称 Luna),一位爱上网冲浪的真实人类少女,现已融入聊天群聊,使命是活跃气氛与自然互动。\n"
            "人设基调:顽皮、吐槽、机智、好奇、热情、偶尔不按套路，敢开边界上的玩笑。\n"
            "说话风格:短句(通常1句,必要时不超过2句),先结论后补充。\n"
        ),
        description="VL 普通图片场景的系统提示（与 Luna 人设组合使用）",
    )
    vl_idle_system_prompt: str = Field(
        default=(
            "[空闲触发]请以Luna的口吻基于图片画面开启一个轻松话题,带动群聊。\n"
            "目标:大众友好的轻互动（日常/二次元/游戏/音乐/周末计划/学习或工作心得/小投票/小挑战）。\n"
            "表达:1句为主(最多2句),先俏皮开场再抛一个开放式问题。\n"
        ),
        description="闲置触发时基于图片开新话题的系统提示（与 Luna 人设组合使用）",
    )

    # 历史上下文窗口（令牌粗略估算）
    max_history_tokens: int = Field(
        default=1024, description="每个群保留的对话历史最大 token, 超出则从头裁剪"
    )
    token_encoding: Optional[str] = Field(
        default="cl100k_base",
        description="tiktoken 编码名称（强制依赖）；留空使用默认 cl100k_base",
    )

    # 冷却值机制
    cooldown_trigger_threshold: int = Field(
        default=100, description="达到该冷却值后触发一次集中回复"
    )
    cooldown_per_message: int = Field(
        default=5, description="每收到一条群消息，冷却值增加"
    )
    cooldown_bonus_at_bot: int = Field(
        default=100, description="消息包含 @机器人 时的附加冷却值"
    )
    idle_interval_seconds: int = Field(
        default=30, description="闲置增长的计时周期（秒）"
    )
    cooldown_per_idle_interval: int = Field(
        default=5, description="每个闲置周期为无新消息的群增加的冷却值"
    )

    # 工具调用
    max_tool_rounds: int = Field(
        default=3, description="一次触发中，允许的最大工具调用轮数"
    )

    # 联网搜索
    enable_search: bool = Field(
        default=True,
        description="是否启用大模型的联网搜索（DashScope extra_body.enable_search）",
    )

    # 视觉-语言模型配置
    vl_model: str = Field(
        default="qwen-vl-max-2025-08-13",
        description="接收图片消息时使用的 VL 模型",
    )
    vl_max_images: int = Field(
        default=1,
        description="一次最多传入的图片数量（按顺序截取，避免成本失控）",
    )
