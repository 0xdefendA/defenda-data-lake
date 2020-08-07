from utils.dict_helpers import sub_dict, enum_keys, dict_match
from utils.dotdict import DotDict
from utils.dates import toUTC
import chevron

class message(object):

    def __init__(self):
        '''
        handle gsuite login activity record
        '''

        self.registration = ['kind']
        self.priority = 20

    def onMessage(self, message, metadata):
        # for convenience, make a dot dict version of the message
        dot_message=DotDict(message)

        # double check that this is our target message
        if 'admin#reports#activity' not in dot_message.get('details.kind','')\
            or 'id' not in message.get('details','') \
            or 'etag' not in message.get('details',''):
            return(message, metadata)

        message["source"]="gsuite"
        message["tags"].append("gsuite")

        # clean up ipaddress field
        if 'ipaddress' in message['details']:
            message['details']['sourceipaddress']=message['details']['ipaddress']
            del message['details']['ipaddress']

        # set the actual time
        if dot_message.get("details.id.time",None):
            message['utctimestamp']=toUTC(message['details']['id']['time']).isoformat()

        # set the user_name
        if dot_message.get("details.actor.email",None):
            message["details"]["user"]=dot_message.get("details.actor.email","")

        # set summary
        message["summary"]=chevron.render("{{details.user}} {{details.events.0.name}} from IP {{details.sourceipaddress}}",message)


        # set category
        message['category']="authentication"

        #success/failure
        if 'fail' in message["summary"]:
            message["details"]["success"]=False
        if 'success' in message["summary"]:
            message["details"]["success"]=True

        #suspicious?
        suspicious={"boolvalue":True,"name":"is_suspicious"}
        for e in dot_message.get("details.events",[]):
            for p in e.get("parameters",[]):
                if dict_match(suspicious,p):
                    message["details"]["suspicious"]=True

        return (message, metadata)