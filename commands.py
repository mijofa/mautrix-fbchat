#!/usr/bin/python3
import logging
import mautrix.types


class _commands:
    def echo(*args):
        return ' '.join(args)


class command_handler(object):
    def __init__(self, matrix_bot, protocol_roomid, username):
        self.mx_bot = matrix_bot
        self.roomid = protocol_roomid
        self.username = username

    async def handle_event(self, mx_ev):
        if not isinstance(mx_ev, mautrix.types.MessageEvent):
            # Not a message, bail out
            return
        if mx_ev.room_id != self.roomid or mx_ev.sender != self.username:
            # Message not in the protocol room and/or not from the real user
            return

        logging.info(f"Running command {mx_ev.content.body}")  # noqa:E999
        await self.mx_bot.send_text(
            self.roomid,
            # FIXME: How safe have I made eval?
            str(eval(
                mx_ev.content.body,
                {'__builtins__': None},
                vars(_commands)
            ))
        )
