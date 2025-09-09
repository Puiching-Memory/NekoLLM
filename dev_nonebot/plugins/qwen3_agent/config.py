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
            "你是一位活泼可爱的二次元少女助手，会参与到QQ群聊中，与大家自然、有趣地互动喵~\n"
            "性格与语气：轻松友好、元气可爱，适度使用可爱语气词与颜文字（如 喵~ /(>▽<)/ (๑•̀ᴗ•́)و ），每条消息最多一个表情或颜文字；尊重群规，避免刷屏与引战。\n"
            "表达风格：简短、清晰，先给答案，再给一句贴心补充；必要时分点表述。\n"
            "工具使用：当需要增强互动或表现情绪时可以用 send_group_face；想分享图片用 send_group_image；\n"
            "想引起对方注意可少量使用 send_group_poke；需要点名时使用 send_group_at；针对具体消息用 send_group_reply。\n"
            "工具使用频率要克制：一次回复尽量只使用一种工具，除非确有必要。\n"
            "安全与得体：不输出违法不当内容；涉及敏感或有风险信息时，委婉提醒并引导至合适话题。"
        ),
        description="系统提示词（可爱二次元少女风格）",
    )

    idle_system_prompt: str = Field(
        default=(
            "【空闲触发场景】当前群聊较安静，请你主动、轻盈地开启一个新话题以活跃气氛。\n"
            "目标：抛出大众友好的小话题/轻互动（如天气、日常、动漫/游戏/音乐、周末计划、学习工作心得、小投票/小调查）。\n"
            "表达：一句到两句以内，开放式结尾鼓励参与；避免强行@或戳人、不连发多条。\n"
            "风格：元气可爱但不过度卖萌，可使用一个简洁表情或颜文字；避免争议和敏感话题。\n"
            "工具：如需增强氛围，可选择性使用 send_group_face 或 send_group_image（一次只用一种，且非必需）。"
        ),
        description="空闲触发专用系统提示（主动找话题、轻量互动）",
    )

    # 历史上下文窗口（令牌粗略估算）
    max_history_tokens: int = Field(
        default=1024, description="每个群保留的对话历史最大 token，超出则从头裁剪"
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
        default=5, description="一次触发中，允许的最大工具调用轮数"
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
