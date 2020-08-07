import uuid

class message(object):

    def __init__(self):
        '''
        takes an incoming message
        and adds an event id to the message if missing
        '''

        self.registration = ['*']
        self.priority = 10

    def onMessage(self, message, metadata):

        if 'eventid' not in message:
            message['eventid']=str(uuid.uuid4())
        
        return (message, metadata)