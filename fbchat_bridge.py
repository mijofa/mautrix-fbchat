#!/usr/bin/python3
import logging

import fbchat


class Client(fbchat.Client):
    def __init__(self, *args, matrix_bot, matrix_protocol_roomid, **kwargs):
        super().__init__(*args, **kwargs)
        self.mx_bot = matrix_bot
        self.mx_protocol_roomid = matrix_protocol_roomid

    async def handle_matrix_event(self, mx_ev):
        logging.debug(mx_ev)

    async def listen(self, markAlive=None):
        print("Running")
        if markAlive is not None:
            self.setActiveStatus(markAlive)

        self.startListening()
        self.onListening()

        print("Loop")
        import asyncio
        while self.listening and self.doOneListen():
            print("Looping...")
            await asyncio.sleep(0)

        self.stopListening()

#    def doOneListen(self, *args, **kwargs):
#        logging.critical('start')
#        super().doOneListen(self, *args, **kwargs)
#        logging.critical('next')

    ### Facebook event handlers
#    def onLoggingIn(self, email=None):
#        """
#        Called when the client is logging in
#
#        :param email: The email of the client
#        """
#        logging.info("Logging in {}...".format(email))
#
#    def on2FACode(self):
#        """Called when a 2FA code is needed to progress"""
#        return input("Please enter your 2FA code --> ")
#
#    def onLoggedIn(self, email=None):
#        """
#        Called when the client is successfully logged in
#
#        :param email: The email of the client
#        """
#        logging.info("Login of {} successful.".format(email))
#
#    def onListening(self):
#        """Called when the client is listening"""
#        logging.info("Listening...")
#
#    def onListenError(self, exception=None):
#        """
#        Called when an error was encountered while listening
#
#        :param exception: The exception that was encountered
#        :return: Whether the loop should keep running
#        """
#        logging.exception("Got exception while listening")
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
        logging.info("{} from {} in {}".format(message_object, thread_id, thread_type.name))

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
        logging.info(
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
        logging.info(
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
        logging.info(
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
        logging.info("{} changed thread image in {}".format(author_id, thread_id))

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
        logging.info(
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
        logging.info("{} added admin: {} in {}".format(author_id, added_id, thread_id))

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
        logging.info("{} removed admin: {} in {}".format(author_id, removed_id, thread_id))

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
#            logging.info("{} activated approval mode in {}".format(author_id, thread_id))
#        else:
#            logging.info("{} disabled approval mode in {}".format(author_id, thread_id))

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
        logging.info(
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
        logging.info((f"Messages {msg_ids} delivered to {delivered_for} in"  # noqa: E999
                       f"{thread_id} ({thread_type.name}) at {ts/1000}s"  # noqa: E999
                       f"META {metadata} MSG {msg}"))  # noqa: E999

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
#        logging.info(
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
        logging.info(
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
        logging.info(
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
        logging.info("{} removed: {} in {}".format(author_id, removed_id, thread_id))

    def onFriendRequest(self, from_id=None, msg=None):
        """
        Called when the client is listening, and somebody sends a friend request

        :param from_id: The ID of the person that sent the request
        :param msg: A full set of the data recieved
        """
        # Is that before or after it's accepted?
        logging.info("Friend request from {}".format(from_id))

    def onInbox(self, unseen=None, unread=None, recent_unread=None, msg=None):
        """
        .. todo::
            Documenting this

        :param unseen: --
        :param unread: --
        :param recent_unread: --
        :param msg: A full set of the data recieved
        """
        logging.info("Inbox event: {}, {}, {}".format(unseen, unread, recent_unread))

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
#        logging.info(
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
#        logging.info(
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
#        logging.info(
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
        logging.info(
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
        logging.info(
            "{} unblocked {} ({}) thread".format(author_id, thread_id, thread_type.name)
        )

#    def onLiveLocation(
#        self,
#        mid=None,
#        location=None,
#        author_id=None,
#        thread_id=None,
#        thread_type=None,
#        ts=None,
#        msg=None,
#    ):
#        """
#        Called when the client is listening and somebody sends live location info
#
#        :param mid: The action ID
#        :param location: Sent location info
#        :param author_id: The ID of the person who sent location info
#        :param thread_id: Thread ID that the action was sent to. See :ref:`intro_threads`
#        :param thread_type: Type of thread that the action was sent to. See :ref:`intro_threads`
#        :param ts: A timestamp of the action
#        :param msg: A full set of the data recieved
#        :type location: models.LiveLocationAttachment
#        :type thread_type: models.fbchat.models.ThreadType
#        """
#        logging.info(
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
#        logging.info(
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
#        logging.info(
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
#        logging.info(
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
#        logging.info(
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
#        logging.info(
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
#        logging.info(
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
#        logging.info(
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
#        logging.info(
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
#        logging.info(
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
#            logging.info(
#                "{} will take part in {} in {} ({})".format(
#                    author_id, plan, thread_id, thread_type.name
#                )
#            )
#        else:
#            logging.info(
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
        logging.info("Ready & listening")

    def onChatTimestamp(self, buddylist=None, msg=None):
        """
        Called when the client receives chat online presence update

        :param buddylist: A list of dicts with friend id and last seen timestamp
        :param msg: A full set of the data recieved
        """
        logging.debug("Chat Timestamps received: {}".format(buddylist))

    # How is this different from the one above?
    def onBuddylistOverlay(self, statuses=None, msg=None):
        """
        Called when the client is listening and client receives information about friend active status

        :param statuses: Dictionary with user IDs as keys and :class:`models.ActiveStatus` as values
        :param msg: A full set of the data recieved
        :type statuses: dict
        """
        logging.debug("Buddylist overlay received: {}".format(statuses))

#    def onUnknownMesssageType(self, msg=None):
#        """
#        Called when the client is listening, and some unknown data was recieved
#
#        :param msg: A full set of the data recieved
#        """
#        logging.debug("Unknown message received: {}".format(msg))
#
#    def onMessageError(self, exception=None, msg=None):
#        """
#        Called when an error was encountered while parsing recieved data
#
#        :param exception: The exception that was encountered
#        :param msg: A full set of the data recieved
#        """
#        logging.exception("Exception in parsing of {}".format(msg))
