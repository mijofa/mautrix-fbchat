#!/usr/bin/python3
import argparse
import asyncio
import datetime
import logging
import sys
import time
import urllib

import yaml

import mautrix
import mautrix.client.api.types

import fbchat_bridge
import commands


# GOTCHAS:
# * alias_localpart is the part between '#' and ':', non-inclusive.
#   It seemed intuitive that it would include the '#' but it doesn't. Many hours were wasted on this.
# * When using a room alias where a room ID is needed, Synapse responds with "MGuestAccessForbidden".
#   That is not a very intuitive error for the actual issue.

class asyncLogger(logging.Handler):
    """Log to a Matrix chat room using async/await syntax"""
    def __init__(self, *args, matrix_intent, matrix_roomid, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLevel(logging.INFO)

        self.matrix_intent = matrix_intent
        self.matrix_roomid = matrix_roomid
        self.queue = asyncio.Queue()
        # FIXME: I don't actually know what ensure_future means
        asyncio.ensure_future(self.emit_listener())

    async def emit_listener(self):
        while True:
            log_msg = await self.queue.get()
            print(log_msg, file=sys.stderr)
            await self.matrix_intent.send_text(self.matrix_roomid, log_msg)
            self.queue.task_done()

    def emit(self, record):
        try:
            self.queue.put_nowait(self.format(record))
        except Exception:
            self.handleError(record)


async def main(
        matrix_baseurl,
        as_token,
        hs_token,
        sender_localpart,
        matrix_domain,
        matrix_user_localpart,
        fbchat_username,
        fbchat_uid,
        fbchat_session,
        url,
        **kwargs):
    protocol_room_alias = f"fbchat_{fbchat_uid}_protocol"

    # matrix_puppet = mautrix.client.Client()
    matrix_appservice = mautrix.AppService(
        server=matrix_baseurl,
        domain=matrix_domain,
        as_token=as_token,
        hs_token=hs_token,
        bot_localpart=sender_localpart)

    url_parsed = urllib.parse.urlsplit(url)
    async with matrix_appservice.run(host=url_parsed.hostname, port=url_parsed.port) as server:
        server = await server

        matrix_bot = matrix_appservice.intent
        # FIXME: Is this approach evil?
        # The internet's usual approach is to *log in* as the matrix user,
        # I don't want to hand more passwords around.
        # So, instead, I have added the matrix user to the appservice's regexes,
        # and am treating it as another child of the appservice
        matrix_puppet = matrix_bot.user(f"@{matrix_user_localpart}:{matrix_domain}")

        # Make sure the protocol room exists and the bot is a member, for debugging/etc
        try:
            # A lot of functions (such as send_text) don't support room aliases, so save the room ID
            protocol_roomid = (await matrix_bot.get_room_alias(f"#{protocol_room_alias}:{matrix_appservice.domain}")).room_id
        except mautrix.errors.request.MNotFound:
            await matrix_bot.create_room(
                alias_localpart=protocol_room_alias,
                visibility=mautrix.client.api.types.RoomDirectoryVisibility.PRIVATE,
                name="Facebook",
                topic="Protocol & debug info for fbchat appservice",
                is_direct=False,
                invitees=[f"@{matrix_user_localpart}:{matrix_appservice.domain}"],
                # initial_state=,
                # room_version=,
                # creation_content=,
            )
        finally:
            # This is probably unnecessary because the mautrix library does this as needed, but it doesn't hurt.
            # I also think it makes more sense intuitively to do this right here.
            await matrix_bot.ensure_joined(protocol_roomid)
            logging.getLogger().addHandler(asyncLogger(matrix_intent=matrix_bot, matrix_roomid=protocol_roomid))

        facebook_puppet = fbchat_bridge.Client(
            email=fbchat_username,
            password='?',
            session_cookies=fbchat_session,
            max_tries=2,
            matrix_bot=matrix_bot,
            matrix_protocol_roomid=protocol_roomid,
        )
        assert facebook_puppet.isLoggedIn()
        matrix_appservice.matrix_event_handler(facebook_puppet.handle_matrix_event)

        cmd_hdlr = commands.command_handler(
            protocol_roomid=protocol_roomid,
            matrix_bot=matrix_bot,
            username=await matrix_puppet.whoami(),
        )
        matrix_appservice.matrix_event_handler(cmd_hdlr.handle_event)

        # Now that we're set up, start receiving Matrix and Facebook events
        await server.start_serving()
        # fbchat is not written for asyncio usage, so run it in it's own thread
        await asyncio.get_event_loop().run_in_executor(None, facebook_puppet.listen)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(
        description="Matrix appservive to bridge with Facebook Messenger")
    argparser.add_argument(
        'yaml_file',
        type=argparse.FileType('r'),
        help="Config file created with register.py")
    argparser.add_argument(
        '-v', '--verbose',
        action='count',
        help="Print debug output")

    args = argparser.parse_args()
    args.config = yaml.load(args.yaml_file)

    # I could use argparse to get the filename then use the much safer & tider with..as syntax,
    # but I figure letting argparse open the file handle will give much better output when it fails.
    args.yaml_file.close()
    del args.yaml_file

    # FIXME: Is using **vars(...) safe?
    asyncio.run(main(**args.config, verbose=args.verbose))
