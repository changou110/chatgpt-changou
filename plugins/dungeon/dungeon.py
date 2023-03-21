# encoding:utf-8

from bridge.bridge import Bridge
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.expired_dict import ExpiredDict
from config import conf
import plugins
from plugins import *
from common.log import logger

# https://github.com/bupticybee/ChineseAiDungeonChatGPT
class StoryTeller():
    def __init__(self, bot, sessionid, story):
        self.bot = bot
        self.sessionid = sessionid
        bot.sessions.clear_session(sessionid)
        self.first_interact = True
        self.story = story

    def reset(self):
        self.bot.sessions.clear_session(self.sessionid)
        self.first_interact = True

    def action(self, user_action):
        if user_action[-1] != "。":
            user_action = user_action + "。"
        if self.first_interact:
            prompt = """现在来充当一个冒险文字游戏，描述时候注意节奏，不要太快，仔细描述各个人物的心情和周边环境。一次只需写四到六句话。
            开头是，""" + self.story + " " + user_action
            self.first_interact = False
        else:
            prompt = """继续，一次只需要续写四到六句话，总共就只讲5分钟内发生的事情。""" + user_action
        return prompt
    

@plugins.register(name="Dungeon", desc="A plugin to play dungeon game", version="1.0", author="lanvent", desire_priority= 0)
class Dungeon(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info("[Dungeon] inited")
        # 目前没有设计session过期事件，这里先暂时使用过期字典
        if conf().get('expires_in_seconds'):
            self.games = ExpiredDict(conf().get('expires_in_seconds'))
        else:
            self.games = dict()

    def on_handle_context(self, e_context: EventContext):

        if e_context['context'].type != ContextType.TEXT:
            return
        bottype = Bridge().get_bot_type("chat")
        if bottype != "chatGPT":
            return
        bot = Bridge().get_bot("chat")
        content = e_context['context'].content[:]
        clist = e_context['context'].content.split(maxsplit=1)
        sessionid = e_context['context']['session_id']
        logger.debug("[Dungeon] on_handle_context. content: %s" % clist)
        if clist[0] == "$停止冒险":
            if sessionid in self.games:
                self.games[sessionid].reset()
                del self.games[sessionid]
                reply = Reply(ReplyType.INFO, "冒险结束!")
                e_context['reply'] = reply
                e_context.action = EventAction.BREAK_PASS
        elif clist[0] == "$开始冒险" or sessionid in self.games:
            if sessionid not in self.games or clist[0] == "$开始冒险":
                if len(clist)>1 :
                    story = clist[1]
                else:
                    story = "你在树林里冒险，指不定会从哪里蹦出来一些奇怪的东西，你握紧手上的手枪，希望这次冒险能够找到一些值钱的东西，你往树林深处走去。"
                self.games[sessionid] = StoryTeller(bot, sessionid, story)
                reply = Reply(ReplyType.INFO, "冒险开始，你可以输入任意内容，让故事继续下去。故事背景是：" + story)
                e_context['reply'] = reply
                e_context.action = EventAction.BREAK_PASS # 事件结束，并跳过处理context的默认逻辑
            else:
                prompt = self.games[sessionid].action(content)
                e_context['context'].type = ContextType.TEXT
                e_context['context'].content = prompt
                e_context.action = EventAction.CONTINUE