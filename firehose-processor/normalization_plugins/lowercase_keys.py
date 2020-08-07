class message(object):

    def __init__(self):
        '''
        takes an incoming message
        and sets the keys to lowercase
        '''

        self.registration = ['*']
        self.priority = 1

    def onMessage(self, message, metadata):
        def lower_key(in_dict):
            if isinstance(in_dict,dict):
                out_dict = {}
                for key, item in in_dict.items():
                    out_dict[key.lower()] = lower_key(item)
                return out_dict
            elif isinstance(in_dict,list):
                return [lower_key(obj) for obj in in_dict]
            else:
                return in_dict

        message = lower_key(message)
        return (message, metadata)