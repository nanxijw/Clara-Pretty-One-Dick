#Embedded file name: carbonui/util\settings.py
"""
Does persisted settings with last-accessed cache feature and such.
"""
import blue
import os
from carbonui.util.bunch import Bunch
import defaultsetting
import types
import yaml
import traceback
import uthread
from carbon.common.script.util.timerstuff import AutoTimer
from carbonui.util.various_unsorted import GetAttrs
import log

class SettingSection:
    """
    Binary settings file handling
    """

    def __init__(self, name, filepath, autoStoreInterval, service):
        self._name = name
        self._filepath = filepath
        self._dirty = False
        self._service = service
        self.datastore = {}
        self.LoadFromFile(filepath, autoStoreInterval)

    def __str__(self):
        return '%s\nSetting section, %s; holding %s groups.\nFileLocation: %s' % ('-' * 60,
         self._name,
         len(self.datastore),
         repr(self._filepath))

    def __repr__(self):
        s = self.__str__() + '\n'
        for groupName, groupValue in self.datastore.iteritems():
            s += '%s:\n' % groupName
            for settingName, settingValue in groupValue.iteritems():
                s += '    %s: %s\n' % (settingName, settingValue)

        return s

    class Group(dict):
        """
        Wrapper class to make groups more accessible within setting sections
        
        """

        def __init__(self, name, section):
            self.__dict__['name'] = name
            self.__dict__['section'] = section

        def __getattr__(self, attrName):
            if hasattr(self, 'section'):
                return self.section.Get(self.name, attrName)

        def Get(self, attrName, defValue = None):
            retVal = self.__getattr__(attrName)
            if retVal is None:
                return defValue
            return retVal

        def __setattr__(self, attrName, value):
            if hasattr(self, 'section'):
                self.section.Set(self.name, attrName, value)

        Set = __setattr__

        def Release(self):
            self.section = None

        def HasKey(self, attrName):
            return self.section.HasKey(self.name, attrName)

        def Delete(self, attrName):
            self.section.Delete(self.name, attrName)

        def GetValues(self):
            return self.section.GetValues(self.name)

    def LoadFromFile(self, filepath, autoStoreInterval):
        data = None
        try:
            fn = blue.paths.ResolvePath(filepath)
            data = blue.win32.AtomicFileRead(fn)
        except:
            pass

        if data and data[0]:
            try:
                self.datastore = blue.marshal.Load(data[0])
                for k, v in self.datastore.iteritems():
                    self.CreateGroup(k)

            except:
                log.LogError('Error loading settings data file--', str(self))

        self.timeoutTimer = AutoTimer(autoStoreInterval * 1000, self.WriteToDisk)

    def GetValues(self, groupName):
        return self.datastore[groupName]

    def Get(self, groupName, settingName):
        """
        We keep track of last access for each entry - see FlushOldEntries below.
        """
        if groupName not in self.datastore:
            self.CreateGroup(groupName)
        if settingName in self.datastore[groupName]:
            value = self.datastore[groupName][settingName][1]
            self.datastore[groupName][settingName] = (blue.os.GetWallclockTime(), value)
            return value
        else:
            n = settingName
            if type(n) == types.UnicodeType:
                n = n.encode('UTF-8')
            return GetAttrs(defaultsetting, self._name, groupName, n)

    def HasKey(self, groupName, settingName):
        return settingName in self.datastore[groupName]

    def Delete(self, groupName, settingName):
        if self.HasKey(groupName, settingName):
            del self.datastore[groupName][settingName]

    def Set(self, groupName, settingName, value):
        if groupName not in self.datastore:
            self.CreateGroup(groupName)
        self.datastore[groupName][settingName] = (blue.os.GetWallclockTime(), value)
        self.FlagDirty()

    def Remove(self, groupName, settingName = None):
        if groupName in self.datastore:
            group = self.datastore[groupName]
            if settingName:
                if settingName in group:
                    del group[settingName]
            else:
                del self.datastore[groupName]
            self.FlagDirty()

    def CreateGroup(self, groupName):
        if groupName not in self.__dict__:
            self.__dict__[groupName] = self.Group(groupName, self)
        if groupName not in self.datastore:
            self.datastore[groupName] = {}

    def FlagDirty(self):
        self._dirty = True

    def WriteToDisk(self):
        if self._dirty:
            self._dirty = False
            fn = blue.paths.ResolvePathForWriting(self._filepath)
            try:
                if os.access(fn, os.F_OK) and not os.access(fn, os.W_OK):
                    os.chmod(fn, 438)
                k = blue.marshal.Save(self.datastore)
                blue.win32.AtomicFileWrite(fn, k)
            except Exception as e:
                log.LogError('Failed writing to disk', str(self), '-', repr(e))

    def Unload(self):
        self.timeoutTimer = None
        self.FlushOldEntries()
        self.WriteToDisk()

    def Save(self):
        self.FlushOldEntries()
        self.WriteToDisk()

    def FlushOldEntries(self):
        """
        Removes all entries older than lastModified.
        Default value is 6 weeks ago.
        """
        lastModified = blue.os.GetWallclockTime() - const.WEEK * 6
        for k, v in self.datastore.iteritems():
            for key in v.keys():
                if v[key][0] <= lastModified:
                    del v[key]

        self.FlagDirty()

    def SetDatastore(self, datastore):
        self.datastore = datastore

    def GetDatastore(self):
        return self.datastore


class YAMLSettingSection(SettingSection):

    def __init__(self, name, filepath, autoStoreInterval, service):
        SettingSection.__init__(self, name, filepath, autoStoreInterval, service)

    def LoadFromFile(self, filepath, autoStoreInterval):
        data = None
        try:
            fn = blue.paths.ResolvePath(filepath)
            data = blue.win32.AtomicFileRead(fn)
        except:
            pass

        if data and data[0]:
            try:
                yaml.CSafeLoader.add_constructor(u'tag:yaml.org,2002:str', StringToUnicodeConstructor)
                self.datastore = yaml.load(data[0], Loader=yaml.CSafeLoader)
                for k, v in self.datastore.iteritems():
                    self.CreateGroup(k)

            except:
                log.LogError('Error loading settings data file -- ', traceback.format_exc())

        self.timeoutTimer = AutoTimer(autoStoreInterval * 1000, self.WriteToDisk)

    def WriteToDisk(self):
        uthread.new(self._WriterThreadFunc)

    def _WriterThreadFunc(self):
        if self._dirty:
            self._dirty = False
            fn = blue.paths.ResolvePathForWriting(self._filepath)
            try:
                if os.access(fn, os.F_OK) and not os.access(fn, os.W_OK):
                    os.chmod(fn, 438)
                k = yaml.dump(self.datastore, Dumper=yaml.CSafeDumper)
                blue.win32.AtomicFileWrite(fn, k)
            except Exception as e:
                log.LogError('Failed writing to disk', str(self), '-', repr(e))


def LoadBaseSettings():
    """
    Temp, currently used by standalone carbonui
    """
    import __builtin__
    if not hasattr(__builtin__, 'settings'):
        __builtin__.settings = Bunch()
    sections = (('user', session.userid, 'dat'), ('char', session.charid, 'dat'), ('public', None, 'yaml'))

    def _LoadSettingsIntoBuiltins(sectionName, identifier, settingsClass, extension):
        key = '%s%s' % (sectionName, identifier)
        filePath = blue.paths.ResolvePathForWriting(u'settings:/core_%s_%s.%s' % (sectionName, identifier or '_', extension))
        section = settingsClass(sectionName, filePath, 62, service=None)
        __builtin__.settings.Set(sectionName, section)

    for sectionName, identifier, format in sections:
        _LoadSettingsIntoBuiltins(sectionName, identifier, SettingSection, 'dat')

    settings.public.CreateGroup('generic')
    settings.public.CreateGroup('device')
    settings.public.CreateGroup('ui')
    settings.public.CreateGroup('audio')
    settings.user.CreateGroup('tabgroups')
    settings.user.CreateGroup('windows')
    settings.user.CreateGroup('suppress')
    settings.user.CreateGroup('ui')
    settings.user.CreateGroup('cmd')
    settings.user.CreateGroup('localization')
    settings.char.CreateGroup('windows')
    settings.char.CreateGroup('ui')
    settings.char.CreateGroup('zaction')


def StringToUnicodeConstructor(loader, node):
    s = loader.construct_scalar(node)
    return unicode(s)


exports = {'uiutil.SettingSection': SettingSection,
 'uiutil.YAMLSettingSection': YAMLSettingSection}
