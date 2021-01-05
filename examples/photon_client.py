#!/usr/bin/env python3

import logging
import sys
import threading
import time
import os
from kik_unofficial.datatypes.peers import Group, User
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.chatting import IncomingChatMessage, IncomingGroupChatMessage, \
    IncomingStatusResponse, IncomingGroupStatus
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeersInfoResponse
from kik_unofficial.datatypes.xmpp.login import ConnectionFailedResponse

username = sys.argv[1] if len(sys.argv) > 1 else input('Username: ')
password = sys.argv[2] if len(sys.argv) > 2 else input('Password: ')

friends = {}
users = {}
groups = []
dms = []
peer_jid = "0"
focus = False


class InteractiveChatClient(KikClientCallback):
    def on_authenticated(self):
        cli_thread = threading.Thread(target=chat)
        cli_thread.start()

    def on_roster_received(self, response: FetchRosterResponse):
        print("Roster refreshed")
        for peer in response.peers:
            friends[peer.jid] = peer
        for m in response.peers:
            if isinstance(m, Group):
                groups.append(str(m))
            if isinstance(m, User):
                dms.append(str(m))

    def on_chat_message_received(self, chat_message: IncomingChatMessage):
        print("[DM] {}: {}".format(jid_to_dm_username(chat_message.from_jid), chat_message.body))
        """client.send_chat_message(chat_message.from_jid,"hello")"""
        time.sleep(1)

    def on_group_message_received(self, chat_message: IncomingGroupChatMessage):
        global peer_jid, focus
        if chat_message.group_jid == peer_jid or focus is False:
            try:
                print("-------\n[GROUP]jid:{} - {}:\n{}: {}".format(get_group_jid_number(chat_message.group_jid),
                                                                    friends[chat_message.group_jid].name,
                                                                    jid_to_group_display_name(chat_message.from_jid),
                                                                    chat_message.body))
            except:
                print(
                    "XXXXXXXXXXXXX\n[WARNING]UH OH, WE GOT A MESSAGE FROM A GROUP NOT IN THE ROSTER, UNLESS THE PROGRAM IS STARTING RUN /refresh\nXXXXXXXXXXXXX")
                print("-------\n[GROUP]jid:{} - {}:\n{}: {}".format(get_group_jid_number(chat_message.group_jid),
                                                                    "UNKNOWN GROUP",
                                                                    jid_to_group_display_name(chat_message.from_jid),
                                                                    chat_message.body))
        else:
            """print("suppressed message from group ({}) {}".format(get_group_jid_number(chat_message.group_jid), friends[chat_message.group_jid].name))"""

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print("Connection failed")

    def on_status_message_received(self, response: IncomingStatusResponse):
        print(response.status)
        client.add_friend(response.from_jid)

    def on_group_status_received(self, response: IncomingGroupStatus):
        client.request_info_of_users(response.status_jid)
        if response.status.find("has joined") > 0:
            print("-------\n[JOIN]({}){} has joined the group ({})".format(response.status_jid,
                                                            jid_to_group_display_name(response.status_jid),
                                                            get_group_jid_number(response.group_jid)))
        if response.status.find("has left") > 0:
            print("-------\n[LEAVE]({}){} has left the group ({})".format(response.status_jid,
                                                          jid_to_group_display_name(response.status_jid),
                                                          get_group_jid_number(response.group_jid)))

    def on_peer_info_received(self, response: PeersInfoResponse):
        users[response.users[0].jid] = response.users[0]


def jid_to_dm_username(jid):
    return jid.split('@')[0][0:-4]


def query_user(jid):
    if jid in users:
        return users[jid]
    else:
        client.request_info_of_users(jid)
        while jid not in users:
            pass
        return users[jid]


def jid_to_group_display_name(jid):
    return query_user(jid).display_name


def get_group_jid_number(jid):
    return jid.split('@')[0][0:-2]


def chat():
    global peer_jid, focus

    print("Refreshing roster")
    client.request_roster()

    help_str = ("-Usage-\n\n" +
                "/help  -  displays this message\n" +
                "/connect [first letters of username/group jid]  -  Chat with peer\n" +
                "/refresh  -  refreshes roster (if anyone has friended / added you to a group)\n" +
                "/dms  -  list all dms you have open\n" +
                "/groups  -  list all groups you have open\n" +
                "/pic \"path to file.png\"  -  send a pic\n" +
                "/focus  -  this makes only messages from the group your connected to appear\n" +
                "/peer  -  list the peer you are currently connected to\n" +
                "Type a line to send a message.\n")
    print(help_str)

    while True:
        message = input()
        if message.startswith('/'):
            if message.startswith('/connect '):
                for jid in friends:
                    if jid.startswith(message[9:]):
                        print("Chatting with {}".format(get_group_jid_number(jid)))
                        peer_jid = jid
                        break

            elif message.startswith('/refresh'):
                print("Refreshing roster")
                client.request_roster()

            elif message.startswith("/pic "):
                client.send_chat_image(peer_jid, message[6:-1])

            elif message.startswith("/focus"):
                focus = not focus
                print("focus: " + str(focus))

            elif message.startswith("/peer"):
                print(peer_jid)

            elif message.startswith("/help"):
                print(help_str)

            elif message.startswith("/dms"):
                print("-DMS-\n{}".format("\n".join([m for m in dms])))

            elif message.startswith("/groups"):
                groups_str = "-GROUPS-"
                for g in groups:
                    groups_str += "\n[GROUP]jid:" + g.split("_")[0][10:] + " - " + g.split("name=")[1].split(", code=")[
                        0]
                print(groups_str)

        else:
            if peer_jid != "0" and message:
                client.send_chat_message(peer_jid, message)
            elif message is None:
                pass
            else:
                print("you need to connect to someone first, use /connect [name/jid]")


if __name__ == '__main__':
    # set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    stream_handler = logging.FileHandler(os.path.dirname(__file__) + '/' + str(int(time.time() * 1000.0)) + '.log')
    stream_handler.setFormatter(logging.Formatter(KikClient.log_format()))
    logger.addHandler(stream_handler)

    # create the client
    callback = InteractiveChatClient()
    client = KikClient(callback=callback, kik_username=username, kik_password=password)

while True: pass