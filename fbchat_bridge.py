#!/usr/bin/python3
import fbchat
import logging


class Client(fbchat.Client):
    def __init__(self, *args, matrix_bot, matrix_protocol_roomid, **kwargs):
        super().__init__(*args, **kwargs)
        self.mx_bot = matrix_bot
        self.mx_protocol_roomid = matrix_protocol_roomid

    async def handle_matrix_event(self, mx_ev):
        print('thing')
        print(mx_ev)
        logging.debug(mx_ev)
