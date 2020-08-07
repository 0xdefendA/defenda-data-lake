import base64
import json 

class message(object):

    def __init__(self):
        '''
        takes an incoming message
        and adds a base64 representation of the message
        for help in downstream handlers that may flatten json, etc. 
        '''

        self.registration = ['*']
        self.priority = 100

    def onMessage(self, message, metadata):

        j2b64=base64.b64encode(json.dumps(message).encode("utf-8"))
        message['_base64']=j2b64.decode("utf-8")
        
        return (message, metadata)