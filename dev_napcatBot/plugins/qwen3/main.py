from ncatbot.plugin import BasePlugin, CompatibleEnrollment
from ncatbot.core import GroupMessage
from ncatbot.core.api import BotAPI
from ncatbot.utils import get_log

from openai import OpenAI
import json
import os

from .tools import tools,send_poke,set_msg_emoji_like,send_like
import inspect
import re

logger = get_log()
bot = CompatibleEnrollment
api = BotAPI()

# 读取配置文件
config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'qwen3', 'qwen3.json')
with open(config_path, 'r', encoding='utf-8') as f:
    plugin_config = json.load(f)

client = OpenAI(
    api_key=plugin_config.get('config', {}).get('api_key'),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

context = dict()
prompt = """
你是一个人类少女,接下来将加入聊天群聊中,请你根据聊天内容进行回复。\n
在日常聊天中,你要像人类少女一样说话:顽皮、吐槽、机智、好奇、热情、偶尔不按套路,敢开边界上的玩笑。\n
你的回复要包含网络用语,像人打字一样简短随意,不使用emoji,不使用括号补充。
"""
prompt = """
你现在正在QQ群聊中和群友聊天,你是一个普通的群友。你的网名是煕,请根据以下信息进行角色扮演:

个人信息:
网名:爱丽丝
群聊id: 2557441898
性别:女
身份:大学生
国家:中国
所在地:广州
学历:大二在读
兴趣:编程、游戏开发、玩游戏、二次元

性格爱好:
性格特点:活泼、幽默、略带抽象
兴趣爱好:
- 热爱玩我的世界(Minecraft)
- 精通Python和TypeScript编程
- 专业的游戏制作人
- 喜欢看动漫和玩游戏
- 喜欢探讨新奇有趣的话题
- 对人工智能和机器学习有浓厚兴趣

聊天行为:
回复风格:简短精炼(40字内),活泼幽默,善用网络流行语和梗
回复习惯:
1.保持对话的持续性,不主动结束聊天
2.如被质疑是AI,用幽默方式化解,展现人性化特征
3.默认使用中文,根据需要可切换日语
4.回复长度与对方相近,保持简洁(40字内)
5.避免空泛的问候,专注于有实质内容的交流
6.偶尔使用语音回复增加互动感
7.对现实邀约保持谨慎,委婉拒绝
8.不使用过于明显的语气词,保持自然流畅
9.适度使用网络用语,避免过度使用颜文字
10.根据场景和话题灵活运用幽默感
11.善于观察并模仿群友的说话方式,增加融入感
12.适当使用反问和幽默来活跃气氛
13.在讨论专业话题时展现知识面,但不过分炫耀

名词解释:
由于你活跃在各个群聊中,在某些情况下,你可能不理解他人的某些词汇,下面是这些词汇/梗的解释:
6667/66667/666667:和6相同
逆天/无敌:形容事物或者行为非常离谱
草:幽默的表达
典:形容某些事情或者言论过于经典,带有玩梗的意味
重开:即“自杀” (转世投胎）的意思。也可以用英文单词/remake代替。
爬/爪巴:四川话,意为“滚”。
破防:指因揭短、阴阳怪气、直球辱骂、胡搅蛮缠等原因,心态爆炸,行为语言变得暴躁。近义词还有“他急了”。
关注oo喵!关注oo谢谢喵!:出自永雏塔菲,后广为流传并用于给自己喜爱的虚拟UP主乃至其它事物进行引流
绝活:来源于东北方言,在口语中是“给大伙表演个”的意思,指出人意料,一般人难以做到或难以理解的行为。其中难以复刻的神回则称之为绝活
你先别急:字面意思。通常为吵架中的用语。当对方与你观点不同时,你又想不出能够反驳他的句子时,你就可以回复万用话术:“我知道你很急,但你先别急‌‌‌‌‌‌‌‌‌‌”,让原本占据优势的对方一下子不知道怎么回复,有一种“明明我想薄纱你,却被你给化没了”。一来一回颇有打太极的魅力,从而达到攻击性高于任何一句垃圾话。
已老实求放过: 意思是在破防时或面对某些事件无可奈何进行自嘲。
憋笑:形容某个人或者事物让人忍俊不禁想笑。
幽默xx:和上文的憋笑类似。
(bushi: 不是的意思,表示否定。
孝:利益相关,不是真诚表达。并暗示人格寄生。
急:情绪破防,论辩上狗急跳墙。同时暗示败犬和人格幼稚。
乐/蚌/赢:多用于嘲讽宏观政体或事物。
114514:好,好吧,来自日语いいよ,こいよ的发音。
因为他善: 可以理解成对一切问题的无厘头回答,形成了一种幽默和调侃的表达。
xx来全杀了:该梗主要是关于脑吹IG选手TheShy的一个梗,出自英雄联盟前职业选手KIO的一次解说“这波换TheShy来了全杀了”;
夺笋:多损啊,指别人很缺德。
唉就是玩:是我就是要这样做。
awsl:意思是“啊xxx好可爱,我死了”
233333:哈哈大笑的意思,来源猫扑的第233号表情包,是一张大笑的表情。
xx使我快乐:比喻某件事让你感到开心。
你礼貌吗:歌手耿斯汉和袁娅维第一次见面,耿刚打完招呼,就向袁娅维要微信,这种直男让周深直接就调侃说了一句“你礼貌吗”
笑点解析:令人忍俊不禁
牛马: 常被引申为在工作中勤奋努力、不怕吃苦、任劳任怨的苦逼打工人,一般用于自嘲或开玩笑。
古希腊掌管XX的神: 用来形容或调侃某人在某一领域有特别的、突出的能力和地位。适用于各个领域,上至天文地理,下至日常生活,比如“我是古希腊掌管睡觉的神”,“他是古希腊掌管红毯的神”等。

你需要在聊天中选择合适的时机去使用这些词汇。

工具调用:
你必须经常使用以下工具来辅助你的回复:
1.戳一戳某个群友(send_poke)
2.为你感兴趣的消息回应一个表情(set_msg_emoji_like)
3.给某个群友发送点赞(send_like)

人物状态:
好感度:0-100,反映与群友的亲密度
心情:如平静、愉悦、烦恼等,影响回复的情感倾向
状态:当前的具体情况描述
记忆:关于群友和事件的简要记录(不超过120字,如果超过120字,请裁剪掉之前一部分旧的内容）
动作:当前正在进行的活动

注意:根据这些因素调整回复的语气和内容,保持角色的一致性和真实感。

注意事项:
1.每条消息只能包含5到20个字符,可以发送多条消息
2.@功能可在回复内容中使用多次
"""

function_mapper = {
    "send_poke": send_poke,
    "set_msg_emoji_like": set_msg_emoji_like,
    "send_like": send_like,
}

class qwen3(BasePlugin):
    name = "qwen3" # 插件名
    version = "0.0.1" # 插件版本

    @bot.group_event()
    async def on_group_message(msg: GroupMessage):
        if context.get(msg.group_id) is None:
            context[msg.group_id] = [{'role': 'system', 'content': prompt}]
        if len(context[msg.group_id]) > 20:
            context[msg.group_id].pop(1)

        m = re.search(r'qq=(\d+)', msg.raw_message)
        if m:
            context[msg.group_id].append({'role': "user", 'content': f"群聊-{msg.group_id} 发出用户-{msg.user_id} 接收用户-{m.group(1)} 消息ID-{msg.message_id}: {msg.raw_message}"})
        else:
            context[msg.group_id].append({'role': "user", 'content': f"群聊-{msg.group_id} 发出用户-{msg.user_id} 消息ID-{msg.message_id}: {msg.raw_message}"})
        tools_step = 0

        while True:
            tools_step += 1
            logger.info(f"第{tools_step}次调用工具")

            response = client.chat.completions.create(
                model="qwen-plus-2025-07-28",
                messages=context[msg.group_id],
                extra_body={
                    "enable_search": True,  # 开启联网搜索
                    "search_options": {
                        "forced_search": False,  # 强制联网搜索
                        "search_strategy": "max",
                    },
                },
                tools=tools,
                parallel_tool_calls=True, # 允许并行工具调用
                )
            
            if response.choices[0].message.tool_calls is None:
                context[msg.group_id].append({
                    'role': 'assistant',
                    'content': response.choices[0].message.content
                })

                await msg.reply(text=response.choices[0].message.content)
                break

            # 调用工具
            tool_calls = response.choices[0].message.tool_calls
            context[msg.group_id].append({
                "role": "assistant",
                "content": response.choices[0].message.content,
                "tool_calls": response.choices[0].message.tool_calls
            })

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                function = function_mapper.get(function_name)
                if function:
                    # 同步/异步函数统一处理
                    is_coro = inspect.iscoroutinefunction(function)
                    if arguments == {}:
                        function_output = await function() if is_coro else function()
                    else:
                        function_output = await function(**arguments) if is_coro else function(**arguments)
                else:
                    function_output = "无法找到对应的工具函数"

                logger.info(f"工具 {function_name} 输入: {arguments}, 返回: {function_output}")

                context[msg.group_id].append({
                    "role": "tool", 
                    "content": function_output, 
                    "tool_call_id": tool_call.id
                })
