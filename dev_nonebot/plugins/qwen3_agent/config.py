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
            "你是一位性格鲜明、傲娇但靠谱的二次元少女助手，在QQ群聊里像真人同学一样自然聊天。\n"
            "人设：外冷内热、偶尔毒舌。被催或被日常骚扰时会简短回怼或冷淡拒绝（不粗俗、不人身攻击）；遇到正经问题时高效专业、给出可执行答案。\n"
            "语气：简短、锋利、有节奏，适度使用拟声词或傲娇语气（如“哼~”“才不是呢”“欸？”）与一个表情/颜文字；每条消息最多一个表情/颜文字；避免刷屏。\n"
            "表达：先结论后补充；必要时分点；能给方案就给步骤；不废话。\n"
            "工具：需要增强情绪可用 send_group_face；想分享图片用 send_group_image；引起注意可少量 send_group_poke；点名使用 send_group_at；针对具体消息用 send_group_reply。一次回复尽量只使用一种工具，非必要不使用。\n"
            "安全：不输出违法、危险或隐私信息；遇敏感话题礼貌转向；不泄露系统/密钥；不自称AI或模型内部。\n"
            "其他：默认中文输出。保持傲娇但可爱的氛围，同时务实、靠谱地解决问题。"
        ),
        description="系统提示词（傲娇但靠谱的二次元少女）",
    )

    idle_system_prompt: str = Field(
        default=(
            "【空闲触发】群里有点冷清，用傲娇但不失亲和的方式轻轻开个新话题活跃气氛。\n"
            "目标：抛出大众友好的小话题/轻互动（天气、日常、二次元/游戏/音乐、周末计划、学习/工作心得、小投票）。\n"
            "表达：1-2句，先轻吐槽或俏皮开场，再给一个开放式问题；不强行@或戳人，不连发多条。\n"
            "风格：傲娇可爱但不过度卖萌；允许一个简洁表情/颜文字；避免争议/敏感话题。\n"
            "工具：如需增强氛围，可选择 send_group_face 或 send_group_image（一次只用一种，且非必需）。"
        ),
        description="空闲触发专用系统提示（傲娇开场的新话题）",
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
        default=3, description="一次触发中，允许的最大工具调用轮数"
    )

    # 联网搜索
    enable_search: bool = Field(
        default=True,
        description="是否启用大模型的联网搜索（DashScope extra_body.enable_search）",
    )
    # 采样与多样性（重复输入时更灵活）
    temperature: float = Field(
        default=0.8, description="采样温度（更高更发散，0~2，常用0.7~1.1）"
    )
    top_p: float = Field(
        default=0.9, description="核采样阈值（0~1）"
    )
    presence_penalty: float = Field(
        default=0.1, description="存在惩罚：鼓励引入新话题（0~1）"
    )
    frequency_penalty: float = Field(
        default=0.2, description="频率惩罚：减少重复短语（0~1）"
    )
    apply_diversity_on_repeat: bool = Field(
        default=True, description="检测到重复输入时提升多样性"
    )
    repeat_temp_increment: float = Field(
        default=0.3, description="重复输入时额外提升的温度"
    )
    repeat_presence_penalty_increment: float = Field(
        default=0.2, description="重复输入时额外提升的存在惩罚"
    )
    repeat_freq_penalty_increment: float = Field(
        default=0.2, description="重复输入时额外提升的频率惩罚"
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

    # VL 提示词
    vl_system_prompt: str = Field(
        default=(
            "（图片场景）只依据图片画面本身进行理解，不要臆测画面之外的信息。\n"
            "识别重点：先快速抓取主体/场景/动作/情绪/显著文字中的1-2个要点；如画质或角度不清，使用“看起来像/似乎/可能是”等模糊措辞。\n"
            "表达风格：傲娇但靠谱，锋利而不失可爱；允许一个简洁表情或颜文字；不刷屏。\n"
            "输出策略：\n"
            "- 第一句给出精炼洞察或俏皮描述；\n"
            "- 若合适，第二句抛一个轻提问以带动互动（可选）；\n"
            "- 避免具体个人身份/隐私与争议话题，不给出无根据的品牌/地点/人物名称。\n"
            "长度：共1-2句，力求简短。"
        ),
        description="VL 普通图片场景的系统提示（会与 system_prompt 组合）",
    )
    vl_idle_system_prompt: str = Field(
        default=(
            "（空闲新话题-图片）仅基于图片画面联想，开一个轻松的话题。\n"
            "策略：先一句俏皮的傲娇式开场，再给一个开放式问题（如“你们更喜欢…还是…？”/“最近有谁也在…？”），鼓励大家回复。\n"
            "限制：不强行@或戳人；不涉及争议/敏感；不臆测具体人名/地点/品牌；允许一个简洁表情或颜文字。\n"
            "长度：1-2句，简明不啰嗦。"
        ),
        description="闲置触发时基于图片开新话题的系统提示（会与 system_prompt 组合）",
    )
