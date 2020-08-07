from utils.dict_helpers import enum_keys, merge
from datetime import datetime

class message(object):

    def __init__(self):
        '''
        takes an incoming message
        and ensures it matches our event shell structure
        '''

        self.registration = ['*']
        self.priority = 2

    def onMessage(self, message, metadata):
        # our target shell
        event_shell={
            "utctimestamp": datetime.utcnow().isoformat(),
            "severity": "INFO",
            "summary": "UNKNOWN",
            "category": "UNKNOWN",
            "source": "UNKNOWN",
            "tags": [],
            "plugins":[],
            "details": {}
        }
        # maybe the shell elements are already there?
        event_set=set(enum_keys(event_shell))
        message_set=set(enum_keys(message))
        if not event_set.issubset(message_set):
            # we have work to do
            # merge the dicts letting any message values win
            # if the message lacks any keys, our shell values win
            message=merge(event_shell,message)

        # move any non shell keys to 'details'
        for item in message_set:
            # enum_keys traverses sub dicts, we only move the top level
            # so check if the key is note a core element
            # present in the top level and move it to details
            if item not in event_shell and item in message:
                message['details'][item]=message.get(item)
                del message[item]

        return (message, metadata)