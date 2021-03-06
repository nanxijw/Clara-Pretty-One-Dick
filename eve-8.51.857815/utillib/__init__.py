#Embedded file name: utillib\__init__.py
import blue
import os
import collections

class KeyVal:
    """ A Key/Value store offering both dictionary- and attribute-like access to its members."""
    __guid__ = 'util.KeyVal'
    __passbyvalue__ = 1

    def __init__(self, dictLikeObject = None, **kw):
        self.__dict__ = kw
        if dictLikeObject is not None:
            if isinstance(dictLikeObject, dict):
                self.__dict__.update(dictLikeObject)
            elif isinstance(dictLikeObject, blue.DBRow):
                for k in dictLikeObject.__keys__:
                    self.__dict__[k] = getattr(dictLikeObject, k)

            elif isinstance(dictLikeObject, KeyVal):
                self.__dict__.update(dictLikeObject.__dict__)
            else:
                raise TypeError("%s can only be initialized with dictionaries, key/value pairs or blue.DBRow's. %s isn't one of them." % (self.__guid__, type(dictLikeObject)))

    def __str__(self):
        members = dict(filter(lambda (k, v): not k.startswith('__'), self.__dict__.items()))
        return '%s: %s' % (self.__class__.__name__, members)

    def __repr__(self):
        return '<%s>' % str(self)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def copy(self):
        ret = KeyVal()
        ret.__dict__.update(self.__dict__)
        return ret

    def get(self, key, defval = None):
        return self.__dict__.get(key, defval)

    def Get(self, key, defval = None):
        return self.__dict__.get(key, defval)

    def Set(self, key, value):
        self.__dict__[key] = value


def GetClientUniqueFolderName():
    path = os.path.normpath(blue.paths.ResolvePath(u'app:/').lower())
    path = path.replace('\\', '_').replace(':', '').replace(' ', '_')
    path += u'_' + GetServerName().lower().replace(' ', '_')
    return path


def GetServerName():
    """
    Returns the server name the client is configured to connect to
    """
    serverName = boot.GetValue('server', '')
    if __builtins__.has_key('prefs'):
        serverName = prefs.GetValue('server', serverName)
    for arg in blue.pyos.GetArg():
        if arg.startswith('/server:'):
            serverName = arg.split(':')[1]

    return serverName


def GetServerPort():
    """
    Returns the server port the client is configured to connect to
    """
    serverPort = boot.GetValue('port', '')
    if __builtins__.has_key('prefs'):
        serverPort = prefs.GetValue('port', serverPort)
    for arg in blue.pyos.GetArg():
        if arg.startswith('/port:'):
            serverPort = arg.split(':')[1]

    return int(serverPort)


def GetLoginCredentials():
    """
    Returns the variables sent with the /login parameter as a list of 2 items:
    [<user>, <password>]
    None returned if no /login parameter found.
    
    Format of parameter: /login:<user>:<password>
    """
    for arg in blue.pyos.GetArg()[1:]:
        if arg.startswith('/login:'):
            argParts = arg.split(':')[1:]
            if len(argParts) != 2:
                raise RuntimeError('Format of login parameter incorrect, should be /login:<user>:<password>')
            return argParts


def extractBits(i):
    """
    Returns a list of the index of the bits that are set.
    """
    cur = 1
    ret = []
    while i > 0:
        if i & 1:
            ret.append(cur)
        cur = cur + 1
        i = i >> 1

    return ret


def RegexSubtractSet(startCharacter, endCharacter, characterSet):
    """
    Given a range (start/end characters), and a list of characters within that range to omit,
    RegexSubtractSet will return the result of subtracting the set from the range.
    
    i.e. Given the range [a-z], and set "almn", the result would be "[b-ko-z]"
    """
    if startCharacter > endCharacter:
        return '[]'
    for char in characterSet[:]:
        if char < startCharacter or char > endCharacter:
            characterSet = characterSet.replace(char, '')

    if not characterSet:
        return '[' + startCharacter + '-' + endCharacter + ']'
    startOrd = ord(startCharacter)
    endOrd = ord(endCharacter)
    boundaryOrds = sorted([ (ord(char) - 1, ord(char) + 1) for char in characterSet ])
    finalSet = '['
    lastStop = lastStart = startOrd
    for stopAt, startAt in boundaryOrds:
        if stopAt > lastStop and stopAt > lastStart:
            finalSet += '-'.join((unichr(lastStart), unichr(stopAt)))
            lastStop = stopAt
        elif stopAt == lastStart:
            finalSet += unichr(stopAt)
            lastStop = stopAt
        lastStart = startAt

    if endOrd > startAt:
        finalSet += '-'.join((unichr(startAt), unichr(endOrd)))
    elif endOrd == startAt:
        finalSet += unichr(startAt)
    finalSet += ']'
    return finalSet


class DAG(object):
    """
        Basic directed graph class
    """

    def __init__(self):
        self.graph = collections.defaultdict(lambda : (set(), set()))

    def AddNode(self, node):
        self.graph[node]

    def InsertEdge(self, A, B):
        self.graph[A][0].add(B)
        self.graph[B][1].add(A)

    def RemoveEdge(self, A, B):
        self.graph[A][0].remove(B)
        self.graph[B][1].remove(A)

    def RemoveNode(self, N, stitch = True):
        connections = self.graph[N]
        del self.graph[N]
        for out in connections[0]:
            self.graph[out][1].remove(N)

        for inc in connections[1]:
            self.graph[inc][0].remove(N)

        if stitch:
            for out in connections[0]:
                self.graph[out][1].update(connections[1])

            for inc in connections[1]:
                self.graph[inc][0].update(connections[0])

    def Invert(self):
        for k, v in self.graph.items():
            self.graph[k] = (v[1], v[0])

    def Leaves(self):
        return [ k for k, v in self.graph.iteritems() if not v[0] ]

    def __str__(self):
        return self.graph.__str__()

    def ToDot(self):
        """
            Returns the string representation of this graph in Graphviz .dot format
        """
        retStr = 'digraph graphname {\n'
        for k, v in self.graph.iteritems():
            for dep in v[0]:
                retStr += '%s -> %s\n' % (k, dep)

        retStr += '}'
        return retStr

    def _ListAllCyclesRec(self, k, v, doneStack, currentStack, detectedCycles):
        if k in doneStack:
            return
        if k in currentStack:
            t = currentStack[currentStack.index(k):]
            t.append(k)
            detectedCycles.append(t)
            return
        currentStack.append(k)
        for each in v[0]:
            self._ListAllCyclesRec(each, self.graph[each], doneStack, currentStack, detectedCycles)

        currentStack.pop()
        doneStack.append(k)

    def ListAllCycles(self):
        """
            naive implementation of minimal cycle detection. Will _not_ return all cycles
            as many will be included by other larger/earlier cycles
            -the "in/not in" checks could be optimized by marking the nodes as we go through
        """
        doneStack = []
        currentStack = []
        detectedCycles = []
        for k, v in self.graph.iteritems():
            if k not in doneStack:
                self._ListAllCyclesRec(k, v, doneStack, currentStack, detectedCycles)

        return detectedCycles
