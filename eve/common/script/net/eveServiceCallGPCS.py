#Embedded file name: eve/common/script/net\eveServiceCallGPCS.py
"""
Calls methods on services
"""
import macho
import gpcs

class ServiceCall(gpcs.CoreServiceCall):
    __guid__ = 'gpcs.ServiceCall'

    def _GetRemoteServiceCallVariables(self, session):
        """"
        EVE Implementation of what session variables should be used
        """
        return (session.locationid, session.solarsystemid, session.stationid)

    def _HandleServiceCallWrongNode(self, e, service, sessionVars1, sessionVars2):
        """
        EVE Implementation of handling the wrong node case
        """
        locationid1, solarsystemid1, stationid1 = sessionVars1
        locationid2, solarsystemid2, stationid2 = sessionVars2
        if macho.mode == 'client' and e.payload is not None and service in self.machoNet.serviceInfo:
            if self.machoNet.serviceInfo[service] == 'solarsystem' or self.machoNet.serviceInfo[service] == 'location' and locationid1 == solarsystemid1:
                if solarsystemid1 == solarsystemid2:
                    self.machoNet.SetNodeOfAddress('beyonce', solarsystemid1, e.payload)
            elif self.machoNet.serviceInfo[service] == 'station' or self.machoNet.serviceInfo[service] == 'location' and locationid1 == stationid1:
                if stationid1 == stationid2:
                    self.machoNet.SetNodeOfAddress('station', stationid1, e.payload)
