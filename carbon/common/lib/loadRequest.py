#Embedded file name: carbon/common/lib\loadRequest.py


class PrioritizedLoadRequest(object):

    def __init__(self):
        self.owner = None

    def GetName(self):
        return 'Unknown'

    def GetPriority(self):
        return 0.0

    def Process(self):
        pass
