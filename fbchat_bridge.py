#!/usr/bin/python3
import logging
import asyncio

import mautrix.errors
import mautrix.client.api.types
import fbchat
fbchat.log.setLevel(logging.WARNING)


_fb_rooms_cache = {}
_mx_rooms_cache = {}
_fb_people_cache = {}
_mx_people_cache = {}


def mx_coro(mx, coro):
    """
    Because the Facebook listener runs in an executor, it's not easy to directly inject into mautrix's event loop.
    I've created this function just so it can be done a little less verbosely
    """
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError as e:
        # This is actually the path I *want* it to take
        current_loop = None
        if len(e.args) != 1 or e.args[0] != "no running event loop":
            raise

    if current_loop == mx.loop:
        mx.log.warning("Attempting to run Asyncio co-routine from inside the same event loop, can not return the result")
        current_loop.call_soon_threadsafe(coro)
    else:
        future = asyncio.run_coroutine_threadsafe(
            coro=coro,
            loop=mx.loop,
        )
        return future.result()  # FIXME: Should I include a timeout?


class Person():
    # FIXME: Add a useful __str__ function
    @classmethod
    def _check_cache(cls, fbid: str = None, mxid: str = None):
        # Check the running in-memory cache of people to avoid reinstating duplicate objects all over the place
        if not fbid and not mxid:
            raise Exception("Must have at least one of fbid or mxid")

        if fbid and fbid in _fb_people_cache:
            return _fb_people_cache[fbid]
        elif mxid and mxid in _mx_people_cache:
            return _mx_people_cache[mxid]
        else:
            return None

    def _update_cache(self):
        # Update the in-memory cache of people
        if self.fbid:
            _fb_people_cache[self.fbid] = self
        if self.mxid:
            _mx_people_cache[self.mxid] = self

    @classmethod
    async def async_get_from_mxid(cls, fb_client, mxid: str):
        p = cls._check_cache(mxid=mxid) or cls(
            fb_client=fb_client,
            fbid=(fb_client.uid if mxid == fb_client.mx_puppet_id
                  else mxid.rsplit(':', 1)[0].rsplit('_', 1)[1]),
            mxid=mxid,
        )
        await fb_client.mx.ensure_registered()

        return p

    @classmethod
    def get_from_fbid(cls, fb_client, fbid: str):
        # Will never be called from Mautrix events, so doesn't need an awaitable version
        p = cls._check_cache(mxid=fbid) or cls(
            fb_client=fb_client,
            fbid=fbid,
            mxid=(fb_client.mx_puppet_id if fbid == fb_client.uid
                  else f"@fbchat_{fb_client.uid}_{fbid}:{fb_client.mx.domain}"),
        )
        mx_coro(fb_client.mx, fb_client.mx.ensure_registered())

        return p

    def __init__(self, fb_client, fbid: str, mxid: str):
        self.parent_fb = fb_client
        self.fbid = fbid
        self.mxid = mxid

        self.mx = fb_client.mx.user(self.mxid)

        self._update_cache()

        ## FIXME: Get Facebook name, photo, nicknames, etc.

    def facebook_message(
        self,
        fb_thread_id: str,
        message_object,
        timestamp: str = None,
    ):
        # Looks like I'll have to use some non-printable text in messages sent into Matrix as a deduplication tag
        room = Room.get_from_fbid(fb_client=self.parent_fb, fbid=fb_thread_id)
        # Need to make sure the room has been joined just in case the invite autoaccepter hasn't had enough time.
        mx_coro(self.mx, self.mx.ensure_joined(room.mxid))
        mx_coro(self.mx, self.mx.send_text(room.mxid, message_object.text))

    async def matrix_event(self, mx_ev):
        # FIXME: Don't send messages to Facebook that were sent to Matrix as this bridge, and vice versa
        # Why does Matrix not have a client ID or similar? Facebook has that.
        if isinstance(mx_ev, mautrix.types.MessageEvent):
            room = await Room.async_get_from_mxid(fb_client=self.parent_fb, mxid=mx_ev.room_id)

            self.parent_fb.log.critical(f'Should send message "{mx_ev.content.body}" in {room} from {self}')


class Room():
    # FIXME: Add a useful __str__ function
    @classmethod
    def _check_cache(cls, fbid: str = None, mxid: str = None):
        # Check the running in-memory cache of rooms to avoid reinstating duplicate objects all over the place
        if not fbid and not mxid:
            raise Exception("Must have at least one of fbid or mxid")

        if fbid and fbid in _fb_rooms_cache:
            return _fb_rooms_cache[fbid]
        elif mxid and mxid in _mx_rooms_cache:
            return _mx_rooms_cache[mxid]
        else:
            return None

    def _update_cache(self):
        # Update the in-memory cache of rooms
        if self.fbid:
            _fb_rooms_cache[self.fbid] = self
        if self.mxid:
            _mx_rooms_cache[self.mxid] = self

    @classmethod
    async def async_get_from_mxid(cls, fb_client, mxid: str):
        alias_response = await fb_client.mx.user(fb_client.mx_puppet_id).get_state_event(
            mxid, mautrix.client.api.types.EventType.ROOM_CANONICAL_ALIAS)
        r = cls._check_cache(mxid=mxid) or cls(
            fb_client=fb_client,
            fbid=alias_response['canonical_alias'].rsplit(':', 1)[0].rsplit('_', 1)[1],
            mxalias=alias_response['canonical_alias'],
            mxid=mxid,
        )
        return r

    @classmethod
    def get_from_fbid(cls, fb_client, fbid: str):
        # Will never be called from Mautrix events, so doesn't need an awaitable version
        r = cls._check_cache(mxid=fbid) or cls(
            fb_client=fb_client,
            fbid=fbid,
            mxalias=f"#fbchat_{fb_client.uid}_{fbid}:{fb_client.mx.domain}",
        )
        if not r.mxid:
            try:
                r.mxid = mx_coro(fb_client.mx,
                                 fb_client.mx.get_room_alias(r.mxalias)
                                 )['room_id']
            except mautrix.errors.request.MNotFound:
                r.mxid = mx_coro(fb_client.mx, r._create_in_mx())

        return r

    def __init__(self, fb_client, fbid: str, mxalias: str, mxid: str = None):
        self.fb = fb_client
        self.fbid = fbid
        self.mxalias = mxalias
        self.mxid = mxid

        if not self.mxid and not self.fbid:
            raise Exception("Must initialise Room with at least one of fbid or mxid")

        self._update_fb_info()

    def _update_fb_info(self):
        t = self.fb.fetchThreadInfo(self.fbid)
        assert len(t) == 1
        thread_info = t[self.fbid]
        if thread_info.name:
            self.name = thread_info.name
        if isinstance(thread_info, fbchat.User):
            self.is_direct = True
            self.fb_participants = [thread_info.uid]
            if thread_info.nickname:
                self.name = thread_info.nickname
            self.topic = f"Facebook {'friend' if thread_info.is_friend else 'correspondent'}"
        elif isinstance(thread_info, fbchat.Group):
            self.is_direct = False
            self.fb_participants = list(thread_info.participants)
            if not self.topic:
                self.topic = f"Facebook group chat"
        else:
            raise NotImplementedError(f"Unknown Facebook thread type")

        self._update_cache()

    async def _create_in_mx(self):
        # GOTCHAS:
        # * is_direct doesn't set the m.direct values for the room's creator, only the invitees
        # * mautrix doesn't seem to have any way to get or set the m.direct values directly
        #
        # Workaround is to create the room as the main appservice bot,
        # invite all the attendees including the real user,
        # then remove the bot from the room immediately.

        # FIXME: Should also update the room info such that a new group name in Facebook changes the Matrix room name
        # FIXME: What if the room already exists but the relevant user is not in the room?
        #        Such as when there's new participants in a group chat.

        local_mxalias = self.mxalias.rsplit(':', 1)[0].lstrip('#')
        invitees = ([self.fb.mx_puppet_id] +
                    [f"@fbchat_{self.fb.uid}_{uid}:{self.fb.mx.domain}" for uid in self.fb_participants])
        # invitees.remove(await self.mx.whoami())  # Inviting people already in the room causes an error
        self.fb.log.info(f"Creating Matrix room {local_mxalias}, with participants {invitees}")
        mxid = await self.fb.mx.create_room(
            alias_localpart=local_mxalias,
            visibility=mautrix.client.api.types.RoomDirectoryVisibility.PRIVATE,
            name=self.name,
            topic=self.topic,
            is_direct=self.is_direct,
            invitees=invitees
            # initial_state=,
            # room_version=,
            # creation_content=,
        )
        # Remove the appservice bot from the room
        await self.fb.mx.leave_room(mxid)
        # All appservice users should get joined automatically by the autoaccepter in main.py

        self._update_cache()

        return mxid


class Client(fbchat.Client):
    def __init__(self, *args, matrix_bot, matrix_user_localpart, log, **kwargs):
        super().__init__(*args, **kwargs)
        self.mx = matrix_bot
        self.mx_puppet_id = f"@{matrix_user_localpart}:{matrix_bot.domain}"
        self.log = log

    async def handle_matrix_event(self, mx_ev):
        if isinstance(mx_ev, mautrix.types.MessageEvent):
            if not mx_ev.sender == self.mx_puppet_id:
                # Messages recieved in Matrix by anyone who is not the real user can be ignored
                return

            self.log.debug("Recieved Matrix MessageEvent from puppet id, processing")
            sender = await Person.async_get_from_mxid(fb_client=self, mxid=mx_ev.sender)
            await sender.matrix_event(mx_ev)

    async def listen(self, markAlive=None):
        """
        Complete rewrite of fbchat's listen() function so that it can be turned into an asyncio awaitable.
        Most of it is a copy-paste of the original, except for the 'await' line below
        """
        if markAlive is not None:
            self.setActiveStatus(markAlive)

        self.startListening()
        self.onListening()

        while self.listening:
            await asyncio.get_event_loop().run_in_executor(None, self.doOneListen)

        self.stopListening()

#    def doOneListen(self, *args, **kwargs):
#        self.log.critical('start')
#        super().doOneListen(self, *args, **kwargs)
#        self.log.critical('next')

    ### Facebook event handlers
#    def onLoggingIn(self, email=None):
#        """
#        Called when the client is self.log in
#
#        :param email: The email of the client
#        """
#        self.log.info("Logging in {}...".format(email))
#
    def on2FACode(self):
        """Called when a 2FA code is needed to progress"""
        raise NotImplementedError("No way of getting the 2FA code")
#        return input("Please enter your 2FA code --> ")
#
#    def onLoggedIn(self, email=None):
#        """
#        Called when the client is successfully logged in
#
#        :param email: The email of the client
#        """
#        self.log.info("Login of {} successful.".format(email))
#
#    def onListening(self):
#        """Called when the client is listening"""
#        self.log.info("Listening...")
#
#    def onListenError(self, exception=None):
#        """
#        Called when an error was encountered while listening
#
#        :param exception: The exception that was encountered
#        :return: Whether the loop should keep running
#        """
#        self.log.exception("Got exception while listening")
#        return True

    def onMessage(
        self,
        mid=None,
        author_id=None,
        message=None,
        message_object=None,
        thread_id=None,
        thread_type=fbchat.models.ThreadType.USER,
        ts=None,
        metadata=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody sends a message

        :param mid: The message ID
        :param author_id: The ID of the author
        :param message: (deprecated. Use `message_object.text` instead)
        :param message_object: The message (As a `Message` object)
        :param thread_id: Thread ID that the message was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the message was sent to. See :ref:`intro_threads`
        :param ts: The timestamp of the message
        :param metadata: Extra metadata about the message
        :param msg: A full set of the data recieved
        :type message_object: models.Message
        :type thread_type: models.fbchat.models.ThreadType
        """
        sender = Person.get_from_fbid(fb_client=self, fbid=message_object.author)
        self.log.info(f"Extra message metadata from Faceboook: {metadata}")
        self.log.info(f"All message info from Faceboook: {msg}")
        sender.facebook_message(fb_thread_id=thread_id, message_object=message_object, timestamp=ts)

    def onColorChange(
        self,
        mid=None,
        author_id=None,
        new_color=None,
        thread_id=None,
        thread_type=fbchat.models.ThreadType.USER,
        ts=None,
        metadata=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody changes a thread's color

        :param mid: The action ID
        :param author_id: The ID of the person who changed the color
        :param new_color: The new color
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param metadata: Extra metadata about the action
        :param msg: A full set of the data recieved
        :type new_color: models.ThreadColor
        :type thread_type: models.fbchat.models.ThreadType
        """
        self.log.info(
            "Color change from {} in {} ({}): {}".format(
                author_id, thread_id, thread_type.name, new_color
            )
        )

    def onEmojiChange(
        self,
        mid=None,
        author_id=None,
        new_emoji=None,
        thread_id=None,
        thread_type=fbchat.models.ThreadType.USER,
        ts=None,
        metadata=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody changes a thread's emoji

        :param mid: The action ID
        :param author_id: The ID of the person who changed the emoji
        :param new_emoji: The new emoji
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param metadata: Extra metadata about the action
        :param msg: A full set of the data recieved
        :type thread_type: models.fbchat.models.ThreadType
        """
        self.log.info(
            "Emoji change from {} in {} ({}): {}".format(
                author_id, thread_id, thread_type.name, new_emoji
            )
        )

    def onTitleChange(
        self,
        mid=None,
        author_id=None,
        new_title=None,
        thread_id=None,
        thread_type=fbchat.models.ThreadType.USER,
        ts=None,
        metadata=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody changes the title of a thread

        :param mid: The action ID
        :param author_id: The ID of the person who changed the title
        :param new_title: The new title
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param metadata: Extra metadata about the action
        :param msg: A full set of the data recieved
        :type thread_type: models.fbchat.models.ThreadType
        """
        self.log.info(
            "Title change from {} in {} ({}): {}".format(
                author_id, thread_id, thread_type.name, new_title
            )
        )

    def onImageChange(
        self,
        mid=None,
        author_id=None,
        new_image=None,
        thread_id=None,
        thread_type=fbchat.models.ThreadType.GROUP,
        ts=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody changes the image of a thread

        :param mid: The action ID
        :param author_id: The ID of the person who changed the image
        :param new_image: The ID of the new image
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param msg: A full set of the data recieved
        :type thread_type: models.fbchat.models.ThreadType
        """
        self.log.info("{} changed thread image in {}".format(author_id, thread_id))

    def onNicknameChange(
        self,
        mid=None,
        author_id=None,
        changed_for=None,
        new_nickname=None,
        thread_id=None,
        thread_type=fbchat.models.ThreadType.USER,
        ts=None,
        metadata=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody changes the nickname of a person

        :param mid: The action ID
        :param author_id: The ID of the person who changed the nickname
        :param changed_for: The ID of the person whom got their nickname changed
        :param new_nickname: The new nickname
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param metadata: Extra metadata about the action
        :param msg: A full set of the data recieved
        :type thread_type: models.fbchat.models.ThreadType
        """
        self.log.info(
            "Nickname change from {} in {} ({}) for {}: {}".format(
                author_id, thread_id, thread_type.name, changed_for, new_nickname
            )
        )

    def onAdminAdded(
        self,
        mid=None,
        added_id=None,
        author_id=None,
        thread_id=None,
        thread_type=fbchat.models.ThreadType.GROUP,
        ts=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody adds an admin to a group thread

        :param mid: The action ID
        :param added_id: The ID of the admin who got added
        :param author_id: The ID of the person who added the admins
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param msg: A full set of the data recieved
        """
        self.log.info("{} added admin: {} in {}".format(author_id, added_id, thread_id))

    def onAdminRemoved(
        self,
        mid=None,
        removed_id=None,
        author_id=None,
        thread_id=None,
        thread_type=fbchat.models.ThreadType.GROUP,
        ts=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody removes an admin from a group thread

        :param mid: The action ID
        :param removed_id: The ID of the admin who got removed
        :param author_id: The ID of the person who removed the admins
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param msg: A full set of the data recieved
        """
        self.log.info("{} removed admin: {} in {}".format(author_id, removed_id, thread_id))

#    def onApprovalModeChange(
#        self,
#        mid=None,
#        approval_mode=None,
#        author_id=None,
#        thread_id=None,
#        thread_type=fbchat.models.ThreadType.GROUP,
#        ts=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and somebody changes approval mode in a group thread
#
#        :param mid: The action ID
#        :param approval_mode: True if approval mode is activated
#        :param author_id: The ID of the person who changed approval mode
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param msg: A full set of the data recieved
#        """
#        if approval_mode:
#            self.log.info("{} activated approval mode in {}".format(author_id, thread_id))
#        else:
#            self.log.info("{} disabled approval mode in {}".format(author_id, thread_id))

    def onMessageSeen(
        self,
        seen_by=None,
        thread_id=None,
        thread_type=fbchat.models.ThreadType.USER,
        seen_ts=None,
        ts=None,
        metadata=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody marks a message as seen

        :param seen_by: The ID of the person who marked the message as seen
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param seen_ts: A timestamp of when the person saw the message
        :param ts: A timestamp of the action
        :param metadata: Extra metadata about the action
        :param msg: A full set of the data recieved
        :type thread_type: models.fbchat.models.ThreadType
        """
        self.log.info(
            "Messages seen by {} in {} ({}) at {}s".format(
                seen_by, thread_id, thread_type.name, seen_ts / 1000
            )
        )

    def onMessageDelivered(
        self,
        msg_ids=None,
        delivered_for=None,
        thread_id=None,
        thread_type=fbchat.models.ThreadType.USER,
        ts=None,
        metadata=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody marks messages as delivered

        :param msg_ids: The messages that are marked as delivered
        :param delivered_for: The person that marked the messages as delivered
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param metadata: Extra metadata about the action
        :param msg: A full set of the data recieved
        :type thread_type: models.fbchat.models.ThreadType
        """
        self.log.info((f"Messages {msg_ids} delivered to {delivered_for} in"
                       f"{thread_id} ({thread_type.name}) at {ts/1000}s"
                       f"META {metadata} MSG {msg}"))

#    def onMarkedSeen(
#        self, threads=None, seen_ts=None, ts=None, metadata=None, msg=None
#    ):
#        """
#        Called when the client is listening, and the client has successfully marked threads as seen
#
#        :param threads: The threads that were marked
#        :param author_id: The ID of the person who changed the emoji
#        :param seen_ts: A timestamp of when the threads were seen
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "Marked messages as seen in threads {} at {}s".format(
#                [(x[0], x[1].name) for x in threads], seen_ts / 1000
#            )
#        )

    def onMessageUnsent(
        self,
        mid=None,
        author_id=None,
        thread_id=None,
        thread_type=None,
        ts=None,
        msg=None,
    ):
        """
        Called when the client is listening, and someone unsends (deletes for everyone) a message

        :param mid: ID of the unsent message
        :param author_id: The ID of the person who unsent the message
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param msg: A full set of the data recieved
        :type thread_type: models.fbchat.models.ThreadType
        """
        self.log.info(
            "{} unsent the message {} in {} ({}) at {}s".format(
                author_id, repr(mid), thread_id, thread_type.name, ts / 1000
            )
        )

    def onPeopleAdded(
        self,
        mid=None,
        added_ids=None,
        author_id=None,
        thread_id=None,
        ts=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody adds people to a group thread

        :param mid: The action ID
        :param added_ids: The IDs of the people who got added
        :param author_id: The ID of the person who added the people
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param msg: A full set of the data recieved
        """
        self.log.info(
            "{} added: {} in {}".format(author_id, ", ".join(added_ids), thread_id)
        )

    def onPersonRemoved(
        self,
        mid=None,
        removed_id=None,
        author_id=None,
        thread_id=None,
        ts=None,
        msg=None,
    ):
        """
        Called when the client is listening, and somebody removes a person from a group thread

        :param mid: The action ID
        :param removed_id: The ID of the person who got removed
        :param author_id: The ID of the person who removed the person
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param msg: A full set of the data recieved
        """
        self.log.info("{} removed: {} in {}".format(author_id, removed_id, thread_id))

    def onFriendRequest(self, from_id=None, msg=None):
        """
        Called when the client is listening, and somebody sends a friend request

        :param from_id: The ID of the person that sent the request
        :param msg: A full set of the data recieved
        """
        # Is that before or after it's accepted?
        self.log.info("Friend request from {}".format(from_id))

    def onInbox(self, unseen=None, unread=None, recent_unread=None, msg=None):
        """
        .. todo::
            Documenting this

        :param unseen: --
        :param unread: --
        :param recent_unread: --
        :param msg: A full set of the data recieved
        """
        self.log.info("Inbox event: {}, {}, {}".format(unseen, unread, recent_unread))

    def onTyping(
        self, author_id=None, status=None, thread_id=None, thread_type=None, msg=None
    ):
        """
        Called when the client is listening, and somebody starts or stops typing into a chat

        :param author_id: The ID of the person who sent the action
        :param status: The typing status
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param msg: A full set of the data recieved
        :type typing_status: models.TypingStatus
        :type thread_type: models.fbchat.models.ThreadType
        """
        pass

#    def onGamePlayed(
#        self,
#        mid=None,
#        author_id=None,
#        game_id=None,
#        game_name=None,
#        score=None,
#        leaderboard=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        metadata=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and somebody plays a game
#
#        :param mid: The action ID
#        :param author_id: The ID of the person who played the game
#        :param game_id: The ID of the game
#        :param game_name: Name of the game
#        :param score: Score obtained in the game
#        :param leaderboard: Actual leaderboard of the game in the thread
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            '{} played "{}" in {} ({})'.format(
#                author_id, game_name, thread_id, thread_type.name
#            )
#        )
#
#    def onReactionAdded(
#        self,
#        mid=None,
#        reaction=None,
#        author_id=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and somebody reacts to a message
#
#        :param mid: Message ID, that user reacted to
#        :param reaction: Reaction
#        :param add_reaction: Whether user added or removed reaction
#        :param author_id: The ID of the person who reacted to the message
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param msg: A full set of the data recieved
#        :type reaction: models.MessageReaction
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "{} reacted to message {} with {} in {} ({})".format(
#                author_id, mid, reaction.name, thread_id, thread_type.name
#            )
#        )
#
#    def onReactionRemoved(
#        self,
#        mid=None,
#        author_id=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and somebody removes reaction from a message
#
#        :param mid: Message ID, that user reacted to
#        :param author_id: The ID of the person who removed reaction
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param msg: A full set of the data recieved
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "{} removed reaction from {} message in {} ({})".format(
#                author_id, mid, thread_id, thread_type
#            )
#        )

    def onBlock(
        self, author_id=None, thread_id=None, thread_type=None, ts=None, msg=None
    ):
        """
        Called when the client is listening, and somebody blocks client

        :param author_id: The ID of the person who blocked
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param msg: A full set of the data recieved
        :type thread_type: models.fbchat.models.ThreadType
        """
        self.log.info(
            "{} blocked {} ({}) thread".format(author_id, thread_id, thread_type.name)
        )

    def onUnblock(
        self, author_id=None, thread_id=None, thread_type=None, ts=None, msg=None
    ):
        """
        Called when the client is listening, and somebody blocks client

        :param author_id: The ID of the person who unblocked
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param msg: A full set of the data recieved
        :type thread_type: models.fbchat.models.ThreadType
        """
        self.log.info(
            "{} unblocked {} ({}) thread".format(author_id, thread_id, thread_type.name)
        )

    def onLiveLocation(
        self,
        mid=None,
        location=None,
        author_id=None,
        thread_id=None,
        thread_type=None,
        ts=None,
        msg=None,
    ):
        """
        Called when the client is listening and somebody sends live location info

        :param mid: The action ID
        :param location: Sent location info
        :param author_id: The ID of the person who sent location info
        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
        :param ts: A timestamp of the action
        :param msg: A full set of the data recieved
        :type location: models.LiveLocationAttachment
        :type thread_type: models.fbchat.models.ThreadType
        """
        pass
#        self.log.info(
#            "{} sent live location info in {} ({}) with latitude {} and longitude {}".format(
#                author_id, thread_id, thread_type, location.latitude, location.longitude
#            )
#        )
#
#    def onCallStarted(
#        self,
#        mid=None,
#        caller_id=None,
#        is_video_call=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        metadata=None,
#        msg=None,
#    ):
#        """
#        .. todo::
#            Make this work with private calls
#
#        Called when the client is listening, and somebody starts a call in a group
#
#        :param mid: The action ID
#        :param caller_id: The ID of the person who started the call
#        :param is_video_call: True if it's video call
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "{} started call in {} ({})".format(caller_id, thread_id, thread_type.name)
#        )
#
#    def onCallEnded(
#        self,
#        mid=None,
#        caller_id=None,
#        is_video_call=None,
#        call_duration=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        metadata=None,
#        msg=None,
#    ):
#        """
#        .. todo::
#            Make this work with private calls
#
#        Called when the client is listening, and somebody ends a call in a group
#
#        :param mid: The action ID
#        :param caller_id: The ID of the person who ended the call
#        :param is_video_call: True if it was video call
#        :param call_duration: Call duration in seconds
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "{} ended call in {} ({})".format(caller_id, thread_id, thread_type.name)
#        )
#
#    def onUserJoinedCall(
#        self,
#        mid=None,
#        joined_id=None,
#        is_video_call=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        metadata=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and somebody joins a group call
#
#        :param mid: The action ID
#        :param joined_id: The ID of the person who joined the call
#        :param is_video_call: True if it's video call
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "{} joined call in {} ({})".format(joined_id, thread_id, thread_type.name)
#        )
#
#    def onPollCreated(
#        self,
#        mid=None,
#        poll=None,
#        author_id=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        metadata=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and somebody creates a group poll
#
#        :param mid: The action ID
#        :param poll: Created poll
#        :param author_id: The ID of the person who created the poll
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type poll: models.Poll
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "{} created poll {} in {} ({})".format(
#                author_id, poll, thread_id, thread_type.name
#            )
#        )
#
#    def onPollVoted(
#        self,
#        mid=None,
#        poll=None,
#        added_options=None,
#        removed_options=None,
#        author_id=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        metadata=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and somebody votes in a group poll
#
#        :param mid: The action ID
#        :param poll: Poll, that user voted in
#        :param author_id: The ID of the person who voted in the poll
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type poll: models.Poll
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "{} voted in poll {} in {} ({})".format(
#                author_id, poll, thread_id, thread_type.name
#            )
#        )
#
#    def onPlanCreated(
#        self,
#        mid=None,
#        plan=None,
#        author_id=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        metadata=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and somebody creates a plan
#
#        :param mid: The action ID
#        :param plan: Created plan
#        :param author_id: The ID of the person who created the plan
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type plan: models.Plan
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "{} created plan {} in {} ({})".format(
#                author_id, plan, thread_id, thread_type.name
#            )
#        )
#
#    def onPlanEnded(
#        self,
#        mid=None,
#        plan=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        metadata=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and a plan ends
#
#        :param mid: The action ID
#        :param plan: Ended plan
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type plan: models.Plan
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "Plan {} has ended in {} ({})".format(plan, thread_id, thread_type.name)
#        )
#
#    def onPlanEdited(
#        self,
#        mid=None,
#        plan=None,
#        author_id=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        metadata=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and somebody edits a plan
#
#        :param mid: The action ID
#        :param plan: Edited plan
#        :param author_id: The ID of the person who edited the plan
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type plan: models.Plan
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "{} edited plan {} in {} ({})".format(
#                author_id, plan, thread_id, thread_type.name
#            )
#        )
#
#    def onPlanDeleted(
#        self,
#        mid=None,
#        plan=None,
#        author_id=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        metadata=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and somebody deletes a plan
#
#        :param mid: The action ID
#        :param plan: Deleted plan
#        :param author_id: The ID of the person who deleted the plan
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type plan: models.Plan
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        self.log.info(
#            "{} deleted plan {} in {} ({})".format(
#                author_id, plan, thread_id, thread_type.name
#            )
#        )
#
#    def onPlanParticipation(
#        self,
#        mid=None,
#        plan=None,
#        take_part=None,
#        author_id=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        metadata=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening, and somebody takes part in a plan or not
#
#        :param mid: The action ID
#        :param plan: Plan
#        :param take_part: Whether the person takes part in the plan or not
#        :param author_id: The ID of the person who will participate in the plan or not
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param metadata: Extra metadata about the action
#        :param msg: A full set of the data recieved
#        :type plan: models.Plan
#        :type take_part: bool
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        if take_part:
#            self.log.info(
#                "{} will take part in {} in {} ({})".format(
#                    author_id, plan, thread_id, thread_type.name
#                )
#            )
#        else:
#            self.log.info(
#                "{} won't take part in {} in {} ({})".format(
#                    author_id, plan, thread_id, thread_type.name
#                )
#            )

    def onQprimer(self, ts=None, msg=None):
        """
        Called when the client just started listening

        :param ts: A timestamp of the action
        :param msg: A full set of the data recieved
        """
        self.log.info("Facebook primed")

    def onChatTimestamp(self, buddylist=None, msg=None):
        """
        Called when the client receives chat online presence update

        :param buddylist: A list of dicts with friend id and last seen timestamp
        :param msg: A full set of the data recieved
        """
        return  # OMG shut up!
        self.log.debug("Chat Timestamps received: {}".format(buddylist))

    # How is this different from the one above?
    def onBuddylistOverlay(self, statuses=None, msg=None):
        """
        Called when the client is listening and client receives information about friend active status

        :param statuses: Dictionary with user IDs as keys and :class:`models.ActiveStatus` as values
        :param msg: A full set of the data recieved
        :type statuses: dict
        """
        self.log.debug("Buddylist overlay received: {}".format(statuses))

#    def onUnknownMesssageType(self, msg=None):
#        """
#        Called when the client is listening, and some unknown data was recieved
#
#        :param msg: A full set of the data recieved
#        """
#        self.log.debug("Unknown message received: {}".format(msg))
#
#    def onMessageError(self, exception=None, msg=None):
#        """
#        Called when an error was encountered while parsing recieved data
#
#        :param exception: The exception that was encountered
#        :param msg: A full set of the data recieved
#        """
#        self.log.exception("Exception in parsing of {}".format(msg))
