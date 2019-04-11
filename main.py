#!/usr/bin/python3
import pdb

import argparse
import asyncio
import logging
import urllib
import time

import yaml

import fbchat
import mautrix
import mautrix.client.api.types


# GOTCHAS:
# * alias_localpart is the part between '#' and ':', non-inclusive.
#   It seemed intuitive that it would include the '#' but it doesn't. Many hours were wasted on this.


async def main(
        matrix_baseurl,
        as_token,
        hs_token,
        sender_localpart,
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
        domain='matrix.abrahall.id.au',  # FIXME: Configify this
        as_token=as_token,
        hs_token=hs_token,
        bot_localpart=sender_localpart,
        aiohttp_params={})
    facebook_puppet = fbchat.Client(
        email=fbchat_username,
        password='?',
        session_cookies=fbchat_session,
        max_tries=2)

    url_parsed = urllib.parse.urlsplit(url)
    async with matrix_appservice.run(host=url_parsed.hostname, port=url_parsed.port) as listener:
        await listener
        print(await matrix_appservice.intent.whoami())
        matrix_bot = matrix_appservice.intent
        joined_rooms = await matrix_bot.get_joined_rooms()
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
        else:
            # This is probably unnecessary as the mautrix library does this as needed, but it doesn't hurt.
            # I also think it makes more sense intuitively to do this right here.
            #
            # NOTE: If you get the roomid wrong here (such as using an alias instead of the ID) the error is nonintuitive
            #       mautrix.errors.request.MGuestAccessForbidden: Guest access not allowed
            await matrix_bot.ensure_joined(protocol_roomid)

        # NOTE: If you get the roomid wrong here (such as using an alias instead of the ID) the error is nonintuitive
        #       mautrix.errors.request.MGuestAccessForbidden: Guest access not allowed
        await matrix_bot.send_text(protocol_roomid, 'foobar')
        time.sleep(1)


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
    asyncio.get_event_loop().run_until_complete(main(**args.config, verbose=args.verbose))
