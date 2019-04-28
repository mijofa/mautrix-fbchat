#!/usr/bin/python3
import argparse
import asyncio
import datetime
import logging
import queue
import re
import sys
import threading
import time
import urllib

import yaml

import mautrix
import mautrix.client.api.types
from mautrix.appservice.state_store.pickle import PickleStateStore

import fbchat_bridge
import commands


# GOTCHAS:
# * alias_localpart is the part between '#' and ':', non-inclusive.
#   It seemed intuitive that it would include the '#' but it doesn't. Many hours were wasted on this.
# * When using a room alias where a room ID is needed, Synapse responds with "MGuestAccessForbidden".
#   That is not a very intuitive error for the actual issue.

class asyncLogger(logging.Handler):
    """Log to a Matrix chat room using async/await syntax"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Messages of debug or lower MUST NOT go into the protocol room.
        # Doing so will cause an endless loop
        self.setLevel(logging.INFO)

        self.queue = asyncio.Queue()

    async def log_to_matrix(self, matrix_intent, matrix_roomid):
        while True:
            log_msg = self.format(await self.queue.get())
            await matrix_intent.send_text(matrix_roomid, log_msg)
            self.queue.task_done()

    def emit(self, record):
        try:
            self.queue.put_nowait(record)
        except Exception:
            self.handleError(record)


class invite_acceptor(object):
    """
    Just blindly accept all invites sent to/from appservice users for appservice rooms.
    This is because it just got real annoying trying to accept invites as soon as they were sent.
    """
    def __init__(self, mx, log, user_regexes, room_regexes):
        self.mx = mx
        self.log = log
        self.user_regexes = [re.compile(r) for r in user_regexes]
        self.room_regexes = [re.compile(r) for r in room_regexes]

    async def handle_event(self, mx_ev):
        if (
            not isinstance(mx_ev.content, mautrix.types.MemberStateEventContent) or
            not mx_ev.content.membership == mautrix.types.Membership.INVITE
        ):
            return  # This is not an invite event

        self.log.info(f'{mx_ev.state_key} was invited to join {mx_ev.room_id} by {mx_ev.sender}')

        if not any(r.match(mx_ev.state_key) for r in self.user_regexes):
            # If I understand the protocol correctly,
            # events that make it through this if branch shouldn't even appear to the appservice in the first place
            self.log.info(f'Invite recipient "{mx_ev.state_key}" does not match regexes "{self.user_regexes}"')
            return  # Not sent to an appservice user

        if not mx_ev.sender == (await self.mx.whoami()) and not any(r.match(mx_ev.sender) for r in self.user_regexes):
            self.log.info(f'Sender "{mx_ev.sender}" does not match regexes')
            return  # Not sent by an appservice user

        # The appservice user can't get the canonical alias unless their in the room,
        # so use the sender's user to get the alias instead.
        room_alias = (await self.mx.user(mx_ev.sender).get_state_event(
            mx_ev.room_id, mautrix.client.api.types.EventType.ROOM_CANONICAL_ALIAS))['canonical_alias']
        if not any(r.match(room_alias) for r in self.room_regexes):
            self.log.info(f'Room alias "{room_alias}" does not match regexes')
            return  # Not being invited into an appservice room

        self.log.info(f'Joining {mx_ev.state_key} into {room_alias} ({mx_ev.room_id})')
        # If it's reached this far then it's a valid invite that should be autoaccepted
        return await self.mx.user(mx_ev.state_key).ensure_joined(mx_ev.room_id)


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
        namespaces,
        verbose,
        **kwargs):

    log_handler = asyncLogger()
    logging.basicConfig(
        format='%(levelname)s:%(name)s:%(funcName)s:%(message)s',
        handlers=(log_handler, logging.StreamHandler(None)),
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(max(30 - (10 * verbose), logging.DEBUG))

    protocol_room_alias = f"fbchat_{fbchat_uid}_protocol"

    async def default_query_handler(query):
        logger.warning(f"query made for {query}")

    matrix_appservice = mautrix.AppService(
        server=matrix_baseurl,
        domain=matrix_domain,
        as_token=as_token,
        hs_token=hs_token,
        bot_localpart=sender_localpart,
        query_user=default_query_handler,
        query_alias=default_query_handler,
        # log=logger,
        state_store=PickleStateStore(autosave_file='mx-state.p')
    )

    url_parsed = urllib.parse.urlsplit(url)
    async with matrix_appservice.run(host=url_parsed.hostname, port=url_parsed.port) as server:
        awaitables = []

        matrix_bot = matrix_appservice.intent
        # FIXME: Is this approach evil?
        # The internet's usual approach is to *log in* as the matrix user,
        # I don't want to hand more passwords around.
        # So, instead, I have added the matrix user to the appservice's regexes,
        # and am treating it as another child of the appservice

        # Before creating any rooms, or doing anything really,
        # set up an event handler to autoaccept invites to & from appservice users.
        autoaccepter = invite_acceptor(
            mx=matrix_bot,
            log=logger,
            user_regexes=(ns['regex'] for ns in namespaces['users']),
            room_regexes=(ns['regex'] for ns in namespaces['aliases']),
        )
        matrix_appservice.matrix_event_handler(autoaccepter.handle_event)

        # Make sure the protocol room exists and the bot is a member, for debugging/etc
        try:
            # A lot of functions (such as send_text) don't support room aliases, so save the room ID
            protocol_roomid = (await matrix_bot.get_room_alias(f"#{protocol_room_alias}:{matrix_appservice.domain}")).room_id
        except mautrix.errors.request.MNotFound:
            protocol_roomid = await matrix_bot.create_room(
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
            ## Don't need to join the rooms manually because they'll be joined by the autoaccepter above
            # awaitables.append(matrix_bot.ensure_joined(protocol_roomid))
            # awaitables.append(matrix_puppet.ensure_joined(protocol_roomid))
            awaitables.append(log_handler.log_to_matrix(matrix_intent=matrix_bot, matrix_roomid=protocol_roomid))

        # Log into Facebook
        # The only reason this isn't done earlier is because I want any errors logged into the protocol room
        facebook_puppet = fbchat_bridge.Client(
            email=fbchat_username,
            password='?',
            session_cookies=fbchat_session,
            max_tries=2,
            matrix_bot=matrix_bot,
            matrix_user_localpart=matrix_user_localpart,
            log=logger,
        )
        assert facebook_puppet.isLoggedIn()
        matrix_appservice.matrix_event_handler(facebook_puppet.handle_matrix_event)

        # Set up an event handler for custom commands
        # FIXME: Should this be done earlier to handle Facebook 2FA/etc?
        cmd_hdlr = commands.command_handler(
            protocol_roomid=protocol_roomid,
            matrix_bot=matrix_bot,
            matrix_user_localpart=matrix_user_localpart,
        )
        matrix_appservice.matrix_event_handler(cmd_hdlr.handle_event)

        # Finally actually start the things
        awaitables.append((await server).start_serving())
        awaitables.append(facebook_puppet.listen())

        # Let the user know we've started the things, then wait for all the things (forever)
        logger.info("Ready!")
        await asyncio.gather(*awaitables)

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(
        description="Matrix appservive to bridge with Facebook Messenger")
    argparser.add_argument(
        'yaml_file',
        type=argparse.FileType('r'),
        help="Config file created with register.py")
    argparser.add_argument(
        '-v', '--verbose',
        default=0,
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
