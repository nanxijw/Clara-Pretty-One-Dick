#Embedded file name: carbon/common/script/util\spwriters.py
"""
This file contains the implementation of the serve page writers
Dependencies:
None
"""
import types
import carbon.common.script.util.htmlwriter as htmlwriter
import util
import blue
import carbon.common.script.net.machobase as macho
from service import ROLE_ANY, ROLEMASK_VIEW, ROLE_ADMIN, ROLE_CONTENT, ROLE_GML, ROLE_GMH, ROLE_PROGRAMMER, ROLE_TRANSLATION, ROLE_TRANSLATIONEDITOR, ROLE_TRANSLATIONADMIN, ROLE_TRANSLATIONTESTER
import iocp
import re
import carbon.common.script.sys.crowset as crowset
from scriber import htmlutils

class SPHtmlWriter(htmlwriter.HtmlWriterEx):
    __guid__ = 'htmlwriter.SPHtmlWriter'
    __dependencies__ = []
    BeNice = blue.pyos.BeNice

    def __init__(self, template = 'script:/wwwroot/lib/template/base.html', menu = '', page = '', showMenu = True):
        htmlwriter.HtmlWriterEx.__init__(self, template)
        self.inserts['experiment_list'] = []
        self.showMenu = showMenu
        if macho.mode == 'server':
            self.DB2 = self.session.ConnectToService('DB2')
            self.cache = self.session.ConnectToService('cache')
            self.SP = self.session.ConnectToService('SP')
            self.BSD = self.session.ConnectToService('BSD')
        elif macho.mode == 'proxy':
            self.DB2 = self.session.ConnectToAnyService('DB2')
            self.cache = self.session.ConnectToAnyService('cache')
            self.SP = self.session.ConnectToAnyService('SP')
        if macho.mode in ('server', 'proxy'):
            title = self.SP.Title()
            header = self.SP.Header()
            color = self.SP.Color()
        else:
            title = 'CCP Server Pages'
            header = 'header_gray.jpg'
            color = '#969696'
        self.inserts['spcolor'] = color
        self.inserts['spcorner'] = '/img/%s' % header
        self.inserts['sphint'] = '%s - %s' % (title, prefs.clusterName)
        dCONTENT = not session.role & ROLE_CONTENT
        dADMIN = not session.role & ROLE_ADMIN
        dVIEW = not session.role & ROLEMASK_VIEW
        dPROG = not session.role & ROLE_PROGRAMMER
        dTRL = not session.role & ROLE_TRANSLATION
        dTRE = not session.role & ROLE_TRANSLATIONEDITOR
        dTRADMIN = not session.role & ROLE_TRANSLATIONADMIN
        dTRQA = not session.role & ROLE_TRANSLATIONTESTER
        dPROG = not session.role & ROLE_PROGRAMMER
        if macho.mode == 'server':
            self.AddTopMenu('GM', 'GM', '', '/gm/character.py?action=MyCharacters')
            self.AddTopMenuSub('GM', 'My Characters', '/gm/character.py?action=MyCharacters')
            self.AddTopMenuSub('GM', 'Characters', '/gm/character.py')
            self.AddTopMenuSub('GM', 'Users', '/gm/users.py')
            if hasattr(util, 'hook_AppSpGmItems'):
                self.AddTopMenuSubLine('GM')
                self.AddTopMenuSub('GM', 'Items', '/gm/items.py')
            self.AddTopMenuSub('GM', 'Browser', '/gm/browser.py', disabled=dVIEW)
            self.AddTopMenu('TICKET', 'TICKET', '', '/gm/petition.py')
            self.AddTopMenu('', '', '', '')
            self.AddTopMenu('CONTENT', 'CONTENT', '', '/gd/bsd.py?action=MyOpenRevisions')
            self.AddTopMenuSub('CONTENT', 'My Open Revisions', '/gd/bsd.py?action=MyOpenRevisions', disabled=dCONTENT)
            self.AddTopMenuSub('CONTENT', 'BSD', '/gd/bsd.py?action=ChangeByID')
            self.AddTopMenuSub('CONTENT', 'Cerberus', '/gd/cerberus.py', disabled=dCONTENT)
            try:
                from eve.common.script.util.espwriters import hook_AppSpContentResources
                self.AddTopMenuSub('CONTENT', 'Resources', '/gd/res.py', disabled=dCONTENT)
                self.AddTopMenuSub('CONTENT', 'FSD Resources', '/gd/res2.py', disabled=dCONTENT)
            except ImportError:
                pass

            try:
                from eve.common.script.util.espwriters import hook_AppSpContentTypes
                self.AddTopMenuSub('CONTENT', 'Types', '/gd/types.py', disabled=dCONTENT)
            except ImportError:
                pass

            if hasattr(util, 'hook_AppSpContentWorldSpaces'):
                self.AddTopMenuSub('CONTENT', 'World Spaces', '/gd/worldSpaces.py', disabled=dCONTENT)
            try:
                from eve.common.script.util.espwriters import hook_AppSpContentPaperdolls
                self.AddTopMenuSub('CONTENT', 'Paper dolls', '/gd/paperdolls.py', disabled=dCONTENT)
            except ImportError:
                pass

            self.AddTopMenuSub('CONTENT', 'Entities', '/gd/entities.py', disabled=dCONTENT)
            self.AddTopMenu('MLS', 'MLS', '', '/mls/mls.py')
            self.AddTopMenuSub('MLS', 'Language', '/mls/language.py')
            self.AddTopMenuSub('MLS', 'Texts (Mammon)', '/mls/messages.py')
            if not blue.pyos.packaged:
                self.AddTopMenuSub('MLS', 'FSD Loc Browser', '/localization/fsdLocalizationBrowser.py')
            self.AddTopMenuSubLine('MLS')
            self.AddTopMenuSub('MLS', 'Localization', '/localization/localization.py')
            self.AddTopMenuSub('MLS', 'Localization Management', '/localization/localizationbrowser.py')
            self.AddTopMenu('', '', '', '')
            self.AddTopMenu('INFO', 'INFO', '', '/info/machine.py')
            self.AddTopMenuSub('INFO', 'Machine', '/info/machine.py')
            self.AddTopMenuSub('INFO', 'DB', '/info/db.py')
            self.AddTopMenuSub('INFO', 'Cache', '/info/cache.py')
            self.AddTopMenuSub('INFO', 'Metrics', '/info/metrics.py')
            self.AddTopMenuSub('INFO', 'Online', '/info/online.py')
            self.AddTopMenuSub('INFO', 'Community', '/info/community.py')
            self.AddTopMenuSub('INFO', 'Reports', '/info/reports.py')
            self.AddTopMenuSub('INFO', 'Entities', '/info/cef.py')
            self.AddTopMenuSubLine('INFO')
            self.AddTopMenuSub('INFO', 'Documentation', '/info/doc.py')
            self.AddTopMenuSub('INFO', 'Blue', '/info/blue.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'ProcessHealth', '/info/processhealth.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Python', '/info/python.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Profiler', '/info/profiler.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'CarbonIO', '/info/CarbonIO.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'StacklessIO', '/info/stacklessio.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'LoadService', '/info/loadservice.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Mass Testing', '/info/testing.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'MachoNet', '/info/machoNet.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Zaction', '/info/zaction.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'OAuth2', '/info/oauth2.py')
            self.AddTopMenu('', '', '', '')
            self.AddTopMenu('ADMIN', 'ADMIN', '', '/admin/db.py')
            self.AddTopMenuSub('ADMIN', 'Client', '/admin/client.py', disabled=dADMIN and dPROG)
            self.AddTopMenuSub('ADMIN', 'Counters', '/admin/counters.py', disabled=dADMIN and dPROG)
            self.AddTopMenuSub('ADMIN', 'Errors', '/admin/errors.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'Logs', '/admin/logs.py', disabled=dPROG)
            self.AddTopMenuSub('ADMIN', 'Network', '/admin/network.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'connectionLimits', '/admin/connectionLimits.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'Services', '/admin/services.py', disabled=dADMIN and dPROG)
            self.AddTopMenuSub('ADMIN', 'Sessions', '/admin/sessions.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'Users', '/admin/users.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'LiveUpdates', '/admin/liveUpdates.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'Paparazzi', '/admin/paparazzi.py', disabled=dADMIN)
            self.AddTopMenuSubLine('ADMIN')
            self.AddTopMenuSub('ADMIN', 'Console', '/admin/console.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'DB', '/admin/db.py', disabled=dADMIN)
        elif macho.mode == 'proxy':
            self.AddTopMenu('INFO', 'INFO', '', '/info/blue.py')
            self.AddTopMenuSub('INFO', 'Machine', '/info/machine.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Blue', '/info/blue.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'ProcessHealth', '/info/processhealth.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Python', '/info/python.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Profiler', '/info/profiler.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'CarbonIO', '/info/CarbonIO.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'StacklessIO', '/info/stacklessio.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'MachoNet', '/info/machoNet.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Crest', '/info/crest.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'OAuth2', '/info/oauth2.py')
            self.AddTopMenu('', '', '', '')
            self.AddTopMenu('ADMIN', 'ADMIN', '', '/admin/counters.py')
            self.AddTopMenuSub('ADMIN', 'Counters', '/admin/counters.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'Logs', '/admin/logs.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'Network', '/admin/network.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'connectionLimits', '/admin/connectionLimits.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'Sessions', '/admin/sessions.py', disabled=dADMIN)
            self.AddTopMenuSub('ADMIN', 'Services', '/admin/services.py', disabled=dADMIN)
            self.AddTopMenuSubLine('ADMIN')
            self.AddTopMenuSub('ADMIN', 'Console', '/admin/console.py', disabled=dADMIN)
        elif macho.mode == 'client':
            self.AddTopMenu('INFO', 'INFO', '', '/info/blue.py')
            self.AddTopMenuSub('INFO', 'Machine', '/info/machine.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Blue', '/info/blue.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'ProcessHealth', '/info/processhealth.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Python', '/info/python.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Profiler', '/info/profiler.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'CarbonIO', '/info/CarbonIO.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'StacklessIO', '/info/stacklessio.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'MachoNet', '/info/machoNet.py', disabled=dPROG)
            self.AddTopMenuSub('INFO', 'Zaction', '/info/zaction.py', disabled=dPROG)
        if page != '':
            self.SelectMenu(page)
        if macho.mode == 'server':
            if menu == 'GM':
                self.AddMenu('Characters', 'Characters', '', '/gm/character.py')
                self.AddMenu('Users', 'Users', '', '/gm/users.py')
                if hasattr(util, 'hook_AppSpGmItems'):
                    self.AddMenu('Items', 'Items', '', '/gm/items.py')
                self.AddMenu('Browser', 'Browser', '', '/gm/browser.py')
            elif menu == 'CONTENT':
                self.AddMenu('BSD', 'BSD', '', '/gd/bsd.py')
                if hasattr(util, 'hook_AppSpContentTypes'):
                    self.AddMenu('Types', 'Types', '', '/gd/types.py')
                try:
                    from eve.common.script.util.espwriters import hook_AppSpContentTypes
                    self.AddMenu('World-Spaces', 'World-Spaces', '', '/gd/worldSpaces.py')
                except ImportError:
                    pass

            elif menu == 'MLS':
                self.AddMenu('Messages', 'Texts/Messages', '', '/mls/messages.py')
                self.AddMenu('Translations', 'Translations', '', '/mls/mls.py')
                self.AddMenu('Pickles', 'Pickles', '', '/mls/pickles.py')
            elif menu == 'INFO':
                self.AddMenu('Machine', 'Machine', '', '/info/machine.py')
                self.AddMenu('DB', 'DB', '', '/info/db.py')
                self.AddMenu('Cache', 'Cache', '', '/info/cache.py')
                self.AddMenu('Metrics', 'Metrics', '', '/info/metrics.py')
                self.AddMenu('Online', 'Online', '', '/info/online.py')
                self.AddMenu('Community', 'Community', '', '/info/community.py')
                self.AddMenu('Reports', 'Reports', '', '/info/reports.py')
                self.AddMenu('Blue', 'Blue', '', '/info/blue.py')
                self.AddMenu('Python', 'Python', '', '/info/python.py')
                self.AddMenu('Profiler', 'Profiler', '', '/info/profiler.py')
                self.AddMenu('StacklessIO', 'StacklessIO', '', '/info/stacklessio.py')
                self.AddMenu('MassTesting', 'Mass Testing', '', '/info/testing.py')
                self.AddMenu('MachoNet', 'MachoNet', '', '/info/machoNet.py')
                self.AddMenu('Zaction', 'Zaction', '', '/info/zaction.py')
            elif menu == 'ADMIN':
                self.AddMenu('Client', 'Client', '', '/admin/client.py')
                self.AddMenu('Counters', 'Counters', '', '/admin/counters.py')
                self.AddMenu('DB', 'DB', '', '/admin/db.py')
                self.AddMenu('Errors', 'Errors', '', '/admin/errors.py')
                self.AddMenu('Logs', 'Logs', '', '/admin/logs.py')
                self.AddMenu('Network', 'Network', '', '/admin/network.py')
                self.AddMenu('connectionLimits', 'connectionLimits', '', '/admin/connectionLimits.py')
                self.AddMenu('Users', 'Users', '', '/admin/users.py')
                self.AddMenu('LiveUpdates', 'LiveUpdates', '', '/admin/liveUpdates.py')
                self.AddMenu('Paparazzi', 'Paparazzi', '', '/admin/paparazzi.py')
        elif macho.mode == 'proxy':
            if menu == 'INFO':
                self.AddMenu('Machine', 'Machine', '', '/info/machine.py')
                self.AddMenu('Blue', 'Blue', '', '/info/blue.py')
                self.AddMenu('Python', 'Python', '', '/info/python.py')
                self.AddMenu('Profiler', 'Profiler', '', '/info/profiler.py')
                self.AddMenu('StacklessIO', 'StacklessIO', '', '/info/stacklessio.py')
                self.AddMenu('MachoNet', 'MachoNet', '', '/info/machoNet.py')
                self.AddMenu('Crest', 'Crest', '', '/info/crest.py')
            elif menu == 'ADMIN':
                self.AddMenu('Counters', 'Counters', '', '/admin/counters.py')
                self.AddMenu('Errors', 'Errors', '', '/admin/errors.py')
                self.AddMenu('Logs', 'Logs', '', '/admin/logs.py')
                self.AddMenu('Network', 'Network', '', '/admin/network.py')
                self.AddMenu('connectionLimits', 'connectionLimits', '', '/admin/connectionLimits.py')
        elif macho.mode == 'client':
            if menu == 'INFO':
                self.AddMenu('Blue', 'Blue', '', '/info/blue.py')
                self.AddMenu('Python', 'Python', '', '/info/python.py')
                self.AddMenu('Profiler', 'Profiler', '', '/info/profiler.py')
                self.AddMenu('StacklessIO', 'StacklessIO', '', '/info/stacklessio.py')
                self.AddMenu('Zaction', 'Zaction', '', '/info/zaction.py')
        if menu == '':
            if page == '':
                self.inserts['title'] = ''
            else:
                self.inserts['title'] = page
        elif page == '':
            self.inserts['title'] = menu
        else:
            self.inserts['title'] = '%s - %s' % (menu, page)
        self.inserts['heading'] = self.inserts['title']
        try:
            from eve.common.script.util.espwriters import hook_AppServerPages
            hook_AppServerPages(self, menu)
        except ImportError:
            pass

        if macho.mode != 'client':
            from base import GetServiceSession
            self.session = GetServiceSession('SPHtmlWriter')
            for each in self.__dependencies__:
                setattr(self, each, self.session.ConnectToAnyService(each))

    def CheckAuthorized(self, request, response, session, neededRoles):
        if boot.role == 'client':
            return
        if not session.userid:
            response.Redirect('/auth/logout')
            return
        if not session.role & neededRoles:
            page = request.FullPath()
            page = self.Canonicalize(page.encode('UTF-8'))
            response.Redirect('/unauthorized.py', {'roles': neededRoles,
             'page': page})
            raise RuntimeError('Role not assigned.')

    def GetQueryString(self, skipkeys = []):
        qs = '?'
        q = self.request.QueryStrings()
        for x in q:
            skipIt = False
            for s in skipkeys:
                if s.lower() in x.lower():
                    skipIt = True
                    break

            if skipIt:
                continue
            if x == '':
                continue
            qs += '%s=%s&' % (x, q[x])

        return qs

    def WritePolarisWarning(self):
        if macho.mode == 'server':
            if prefs.clusterMode in ('TEST', 'LIVE'):
                self.machoNet = self.session.ConnectToService('machoNet')
                polarisNodeID = self.machoNet.GetNodeFromAddress(const.cluster.SERVICE_POLARIS, 0)
                if self.machoNet.GetNodeID() != polarisNodeID:
                    polarisExternalAddress = self.machoNet.GetPolarisExternalTunnelingAddress()
                    if polarisExternalAddress:
                        txt = '<br><font color=white size=2>Not running on <a style="color:white;" href="http://%s">POLARIS</a>!</font></b>' % polarisExternalAddress
                        self.inserts['heading'] += txt

    def IsPolaris(self):
        return macho.mode == 'server' and self.machoNet.GetNodeID() == self.machoNet.GetNodeFromAddress(const.cluster.SERVICE_POLARIS, 0)

    def PolarisUrl(self):
        if macho.mode == 'server':
            h = self.request.Host()
            portFromRequest = h[1]
            firstTwoLettersInPortFromRequest = portFromRequest[:2]
            lastThreeLettersInPortFromPolarisInfo = str(sm.GetService('cache').GetPolarisInfo().tunnelingPort)[2:]
            if int(portFromRequest) / 1000 == 10:
                port = '%s' % portFromRequest
            else:
                port = '%s%s' % (firstTwoLettersInPortFromRequest, lastThreeLettersInPortFromPolarisInfo)
            result = 'http://%s:%s' % (h[0], port)
        else:
            tcpproxy = sm.GetService('tcpRawProxyService')
            machoNet = self.session.ConnectToSolServerService('machoNet')
            defaultPort = sm.GetService('machoNet').defaultTunnelPortOffset + 1
            polarisID = machoNet.GetNodeFromAddress(const.cluster.SERVICE_POLARIS, 0)
            result = 'http://%s' % tcpproxy.GetESPTunnelingAddressByNodeID(polarisID).replace('???', str(defaultPort))
        if iocp.UsingHTTPS():
            result = result.replace('http://', 'https://')
        return result

    def PolarisImage(self, url, attr = 'border=0'):
        polaris = self.PolarisUrl()
        return self.Image('%(polaris)s%(url)s' % {'polaris': polaris,
         'url': url}, attr)

    def AppBottomLeft(self):
        usr = ''
        chr = ''
        if macho.mode == 'server':
            usr = '<a style="color:silver;" href="/gm/users.py?action=User&userID=%s">%s</a>' % (session.userid, session.esps.contents['username'])
            if session.charid:
                chr = '<a href="/gm/character.py?action=Character&characterID=%s"><font color=SILVER>%s</font></a>' % (session.charid, self.CharacterName(session.charid))
        elif macho.mode == 'proxy':
            usr = session.esps.contents['username']
        s = ''
        if usr != '':
            s = ' %s User: %s&nbsp;&middot;&nbsp;<a style="color:silver;" href="/auth/logout">Logout</a> ' % (self.MidDot(), usr)
        if chr != '':
            s += ' %s Character: %s' % (self.MidDot(), chr)
        return s

    def AddMainMenuItemHdr(self, txt, name):
        lst = [[txt, name]]
        return lst

    def AddMainMenuItem(self, lst, text, page, image, action = {}, more = ''):
        MAX_COLS = 3
        s = ''
        if text != '':
            s = '\n                <table cellpadding="1" cellspacing="0" width="100%%">\n                    <tr>\n                        <td width="1%%">\n            '
            s += self.Link(page, self.Image('/img/%s' % image, 'border=0 align=absmiddle'), action)
            s += '\n                        </td>\n                        <td><nobr>\n            '
            s += self.Link(page, '<font size=3>%s</font>' % text, action)
            if more:
                s += '<br>%s' % more
            s += '    </nobr></td>\n                    </tr>\n                </table>'
        s = '<td width="33%%" style="border-bottom:1px solid #DEDEDE;">%s</td>\n' % s
        for i in range(len(lst)):
            if i == 0:
                continue
            r = lst[i]
            if len(r) < MAX_COLS:
                r.append(s)
                return

        lst.append([s])

    def GenerateMainMenu(self, lst):
        name = lst[0][1]
        txt = '<table align=center cellpadding=5 cellspacing=0 width="100%%">\n'
        txt += '  <tr>\n                        <td colspan=3 style="cursor:pointer; border-bottom:1px solid #DEDEDE;" OnClick="ToggleMainMenu(\'%s\');"><b>%s</b></td>\n                    </tr>\n                    <tr>\n                        <td><div id="%s">\n                            <table width="100%%" cellspacing=0 cellpadding=3><tr>\n                ' % (name, lst[0][0], name)
        for i in range(len(lst)):
            if i == 0:
                continue
            r = lst[i]
            txt += '<tr>'
            for i in range(len(r)):
                c = r[i]
                txt += c

            txt += '</tr>\n'

        txt += '\n                            </table>\n                        </div>\n                    </td>\n                </tr>\n            </table>'
        txt += '<script type="text/javascript">\n            c = $.cookie("mm_%s");\n            if (c && c == \'none\')\n                ToggleMainMenu(\'%s\');\n            </script>' % (name, name)
        return txt

    def Font(self, html, size = None, color = None, bold = False, italic = False, underlined = False):
        spanClass = ''
        if size:
            spanClass += 'font-%s' % size
        if color:
            spanClass += ' %s' % color
        if bold:
            spanClass += ' strong'
        if italic:
            spanClass += ' italic'
        if underlined:
            html = '<u>%s</u>' % html
        return '<span class="%s">%s</span>' % (spanClass, html)

    def FontBold(self, html):
        return '<strong>%s</strong>' % html

    def FontItalic(self, html):
        return '<em>%s</em>' % html

    def FontUnderlined(self, html):
        return '<u>%s</u>' % html

    def FontColor(self, color, html):
        return '<span class="%s">%s</span>' % (color, html)

    def FontBoldColor(self, color, html):
        return self.FontBold(self.FontColor(color, html))

    def FontRed(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="red%s%s%s">%s</span>' % (inline,
         size,
         padding,
         html)

    def FontBoldRed(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="strong red%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontGreen(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="green%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontBoldGreen(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="strong green%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontGray(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="dark-gray%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontBoldGray(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="strong dark-gray%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontOrange(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="orange%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontBoldOrange(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="strong orange%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontPurple(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="purple%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontBoldPurple(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="strong purple%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontBlue(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="blue%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontBoldBlue(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="strong blue%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontBrown(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="brown%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontBoldBrown(self, html, size = None, padding = None, inline = False):
        inline = ' inline' if inline else ''
        size = ' font-%d' % size if size else ''
        padding = ' padding-%d' % padding if padding else ''
        return '<span class="strong brown%s%s%s">%s</span>' % (size,
         padding,
         inline,
         html)

    def FontProperty(self, html):
        return '<span class="dark-red">%s</span>' % html

    def FontHeaderProperty(self, html):
        return '<strong><span class="dark-red">%s</span></strong>' % html

    def FontName(self, html):
        return '<strong><span class="red">%s</span></strong>' % html

    def WriteRight(self, html):
        self.WriteAligned('right', html)

    def WriteHelp(self, stringList):
        self.WriteBreak(3)
        self.Write('<table border=1 width=100% style="border:1px;" bgcolor=#FFFFF0><tr><td><ul>')
        l = len(stringList)
        i = 0
        for s in stringList:
            self.Write('<li>' + s)
            i += 1
            if i != l:
                self.WriteBreak(2)

        self.Write('</ul></td></tr></table>')

    def CustomActionsNext(self, rs, maxRows, nextAction, nextID, nextDate = None, args = None):
        if len(rs) == maxRows:
            d = {'action': nextAction}
            d[nextID] = rs[maxRows - 1][nextID]
            if nextDate:
                d[nextDate] = util.FmtDateEng(rs[maxRows - 1][nextDate], 'ln')
            if args:
                d.update(args)
            return [self.Button('', 'NEXT', d, 'blue')]
        else:
            return []

    def StrToDateTime(self, dateTime):
        if dateTime is None or dateTime == '':
            return
        else:
            return util.ParseDateTime(dateTime)

    def IsNone(self, value, replaceValue = ''):
        if value is None:
            return replaceValue
        else:
            return value

    def IsBlank(self, value, replaceValue):
        if value == '':
            return replaceValue
        else:
            return value

    def CheckboxInt(self, value):
        if value == 'on':
            return 1
        else:
            return 0

    def NoneStr(self, str):
        if str is None:
            return ''
        else:
            return str

    def EmptyStrNone(self, s):
        if s is not None:
            s = unicode(s).strip()
            if s == '':
                s = None
        return s

    def NoBreakDate(self, s, f = 'ls'):
        if s is not None:
            return '<nobr>%s</nobr>' % util.FmtDateEng(s, f)
        return ''

    def Space(self, c = 3):
        return '&nbsp;' * c

    def MidDot(self, c = 1):
        return '&nbsp;' * c + '&middot;' + '&nbsp;' * c

    def LinesSortByColumn(self, lines, colIndex, caseSensitive = 1):
        if caseSensitive == 1:
            lines.sort(lambda x, y: cmp(x[colIndex], y[colIndex]))
        else:
            lines.sort(lambda x, y: cmp(x[colIndex].lower(), y[colIndex].lower()))

    def LinesSortByLink(self, lines, colIndex, caseSensitive = 1):
        if caseSensitive == 1:
            lines.sort(lambda x, y: cmp(x[colIndex][x[colIndex].find('>'):], y[colIndex][y[colIndex].find('>'):]))
        else:
            lines.sort(lambda x, y: cmp(x[colIndex][x[colIndex].find('>'):].lower(), y[colIndex][y[colIndex].find('>'):].lower()))

    def NiceText(self, s):
        sLen = len(s)
        if sLen == 0:
            return ''
        else:
            i = 0
            sNice = ''
            afterBreak = 0
            while i < sLen:
                sChar = s[i]
                sAdd = sChar
                if sChar == '\n':
                    sAdd = '<br>'
                    afterBreak = 1
                elif sChar == '<':
                    if s[i:i + 4].lower() == '<br>':
                        sAdd = '<br>'
                        i += 3
                        afterBreak = 1
                if afterBreak == 2:
                    if sChar == ' ':
                        sAdd = '&nbsp;'
                    else:
                        afterBreak = 0
                sNice = sNice + sAdd
                i += 1
                if afterBreak == 1:
                    afterBreak = 2

            return sNice

    def BackLink(self, backText = 'BACK'):
        return self.Link('javascript:history.go(-1);', backText)

    def WriteBackLink(self, backText = 'BACK'):
        self.WriteRight(self.BackLink(backText))

    def FmtRight(self, s):
        if s is None:
            return ''
        else:
            return '<div align=right>%s</div>' % s

    def FmtDigitInteger(self, x):
        if x is None:
            return ''
        elif x == 0:
            return '0'
        else:
            if x < 0:
                sign = '-'
            else:
                sign = ''
            a = str(abs(x))
            ret = ''
            for i in xrange(len(a) % 3, len(a) + 3, 3):
                if i < 3:
                    ret = ret + a[:i]
                else:
                    ret = ret + '.' + a[i - 3:i]

            if ret[0] == '.':
                ret = ret[1:]
            return '%s%s' % (sign, ret)

    def FmtDigitIntegerRight(self, x):
        return self.FmtRight(self.FmtDigitInteger(x))

    def SplitAdd(self, s1, s2, split = ', '):
        if s1 == '':
            return self.IsNone(s2, '')
        elif s2 is None or s2 == '':
            return s1
        else:
            return s1 + split + s2

    def GenderText(self, gender):
        if gender == 0:
            return 'Female'
        if gender == 1:
            return 'Male'
        return ''

    def CartesianCoordinates(self, x, y, z):
        return '(%s, %s, %s)' % (x, y, z)

    def ComboGender(self):
        return {0: 'Female',
         1: 'Male'}

    def ComboSortOrder(self):
        return {'a': 'Ascending',
         'd': 'Descending'}

    def ComboRows(self, max = 5000):
        d = {}
        d[10] = '   10'
        d[20] = '   20'
        d[50] = '   50'
        d[100] = '  100'
        d[200] = '  200'
        d[500] = '  500'
        if max >= 1000:
            d[1000] = ' 1000'
        if max >= 2000:
            d[2000] = ' 2000'
        if max >= 5000:
            d[5000] = ' 5000'
        if max >= 10000:
            d[10000] = '10000'
        if max >= 20000:
            d[20000] = '20000'
        return d

    def ComboGraphSize(self):
        return {'L': 'Large',
         'M': 'Medium',
         'S': 'Small'}

    def GraphSizes(self, size):
        if size == 'L':
            return (1400, 320)
        elif size == 'M':
            return (1100, 320)
        else:
            return (700, 320)

    def EnableExperiments(self):
        self.AddCssFile('/static/css/bootstrap.stripped.css')
        self.AddJsFile('/static/js/libs/bootstrap.js')
        self.AddCssFile('/static/css/experimental.css')
        self.AddJsFile('/static/js/experimental.js')
        self.inserts['experiment_list'].append({'label': "What's this then?",
         'icon': 'icon-question-sign',
         'description': 'Curious?',
         'href': 'javascript:e626_infobox_open();'})
        self.inserts['experiment_list'].append({'label': 'Go Fullscreen',
         'icon': 'icon-resize-full',
         'description': 'Hides the left and right menus and the page top and expands the center content',
         'href': 'javascript:e626_fullscreen(this);'})
        if self.SessionVarGet('UseOldDashboard', False):
            self.inserts['experiment_list'].append({'label': 'Enable New Ticket Dashboard',
             'icon': 'icon-plus-sign',
             'description': 'Use the New and Shiny Ticket Dashboard.',
             'href': 'javascript:e626_old_dashboard(this);'})
        else:
            self.inserts['experiment_list'].append({'label': 'Disable New Ticket Dashboard',
             'icon': 'icon-minus-sign',
             'description': 'Switch to the Backup of the Old Ticket Dashboard.',
             'href': 'javascript:e626_old_dashboard(this);'})
        self.WriteDirect('floaters', '<div id="e626_infobox" class="modal hide fade" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" aria-hidden="true">\n              <div class="modal-header">\n                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>\n                <h3 id="myModalLabel">Super secret experimental ESP stuff!</h3>\n              </div>\n              <div class="modal-body">\n                <p>That shiny little menu thing down there with the fire icon contains experimental stuff. As such it might not always work correctly, is not officially supported (but feel free to <a href="mailto:thordurm@ccpgames.com">contact me</a> anyway) and can change without warning. Use at your own discression.</p>\n              </div>\n              <div class="modal-footer">\n                <button class="btn btn-primary" data-dismiss="modal" aria-hidden="true">Ok, got it!</button>\n              </div>\n            </div>')
        self.WriteDirect('floaters', '<div id="fst_box"><a id="fullscreen_trigger" class="btn btn-small btn-primary" href="javascript:e626_normalscreen();" title="Click here to exit Fullscreen mode"><i class="icon-resize-small icon-white icon-smallbutton"></i></a></div>')

    MSG_KEY = 'esp_messages'
    ESP_KEY = 'esp_variables'

    def SessionVarSet(self, name, value):
        if session:
            varmap = session.GetSessionVariable(self.ESP_KEY, {})
            varmap[name] = value
            session.SetSessionVariable(self.ESP_KEY, varmap)

    def SessionVarGet(self, name, default = None):
        if session:
            varmap = session.GetSessionVariable(self.ESP_KEY, {})
            if name in varmap:
                return varmap[name]
        return default

    def SessionVarGetAll(self, name, default = None):
        if session:
            return session.GetSessionVariable(self.ESP_KEY, {})
        return default

    def SessionVarClear(self, name):
        if session:
            varmap = session.GetSessionVariable(self.ESP_KEY, {})
            if name in varmap:
                del varmap[name]
            session.SetSessionVariable(self.ESP_KEY, varmap)

    def SessionVarClearAll(self):
        if session:
            session.SetSessionVariable(self.ESP_KEY, {})

    def SessionVarPop(self, name, default = None):
        value = self.SessionVarGet(name, default)
        self.SessionVarClear(name)
        return value

    def SessionMsgAdd(self, message):
        """Stores a "fire-an-forget" message in a list of such messages in
        the session. Prepending the message with selected tags controls the
        state (color) and icon of the message output:
        
            - "Hello World!" (default) or "ok::Hello World!" displays
              "Hello World!" in an ok box
            - "info::Hello World!" displays "Hello World!" in an info box
            - "warning::Hello World!" displays "Hello World!" in a warning box
            - "error::Hello World!" displays "Hello World!" in an error box
        
        :type message: basestring
        """
        if session:
            messageList = session.GetSessionVariable(self.MSG_KEY)
            if messageList:
                if isinstance(messageList, list):
                    messageList.append(message)
                else:
                    messageList = [messageList, message]
            else:
                messageList = [message]
            session.SetSessionVariable(self.MSG_KEY, messageList)

    def SessionMsgFlush(self):
        """Flushes all session messages from the session and returns a list of
        them.
        
        :rtype: list
        """
        if session:
            messageList = session.GetSessionVariable(self.MSG_KEY, [])
            session.SetSessionVariable(self.MSG_KEY, [])
            if isinstance(messageList, list):
                return messageList
            else:
                return [messageList]

    def SessionMsgGetRendered(self):
        if hasattr(self, 'response') and not getattr(self.response, 'done', False):
            self.AddCss('/static/css/ccp-jquery-ui.css')
            messageList = self.SessionMsgFlush()
            renderedList = []
            if messageList:
                for message in messageList:
                    if message.startswith('error::'):
                        renderedList.append(self.HtmlAlertBoxError(message[7:]))
                    elif message.startswith('warning::'):
                        renderedList.append(self.HtmlAlertBoxWarning(message[9:]))
                    elif message.startswith('info::'):
                        renderedList.append(self.HtmlAlertBoxInfo(message[6:]))
                    elif message.startswith('ok::'):
                        renderedList.append(self.HtmlAlertBoxOk(message[4:]))
                    else:
                        renderedList.append(self.HtmlAlertBoxOk(message))

            return ''.join(renderedList)
        return ''

    def _SessionMsgRender(self):
        """Writes out and flushes all temporary fire-and-forget Session Messages.
        See SessionMsgAdd for details"""
        if hasattr(self, 'response') and not getattr(self.response, 'done', False):
            self.AddCss('/static/css/ccp-jquery-ui.css')
            messageList = self.SessionMsgFlush()
            if messageList:
                for message in messageList:
                    if message.startswith('error::'):
                        self.WriteDirect('sessionMessages', self.HtmlAlertBoxError(message[7:]))
                    elif message.startswith('warning::'):
                        self.WriteDirect('sessionMessages', self.HtmlAlertBoxWarning(message[9:]))
                    elif message.startswith('info::'):
                        self.WriteDirect('sessionMessages', self.HtmlAlertBoxInfo(message[6:]))
                    elif message.startswith('ok::'):
                        self.WriteDirect('sessionMessages', self.HtmlAlertBoxOk(message[4:]))
                    else:
                        self.WriteDirect('sessionMessages', self.HtmlAlertBoxOk(message))

    def HtmlAlertBox(self, message, state = 'success', icon = 'ok', closable = True):
        """Returns HTML code for a Bootstrap alert box
        
        :type message: basestr
        :param state: Uses the CSS alert states from Bootstrap (sans the
                      preceding "alert-"). See
                      http://twitter.github.io/bootstrap/components.html#alerts
        :type state: str
        :param icon: Uses the Icon clyphs from Bootstrap (sans the preceding
                     "icon-"). See:
                     http://twitter.github.io/bootstrap/base-css.html#icons
        :type icon: str
        :rtype: basestring
        """
        if icon:
            icon = '<i class="icon-%s"></i> ' % icon
        if state:
            state = ' alert-%s' % state
        if closable:
            closable = '<button type="button" class="close" data-dismiss="alert">&times;</button>'
        else:
            closable = ''
        return '<div class="fade in alert%s">%s%s%s</div>' % (state,
         closable,
         icon,
         message)

    def HtmlAlertBoxOk(self, message, closable = True):
        """Shortcut for HtmlAlertBox() usinf "success" state and "ok" icon
        
        :type message: basestr
        """
        return self.HtmlAlertBox(message, 'success', 'ok', closable)

    def HtmlAlertBoxInfo(self, message, closable = True):
        """Shortcut for HtmlAlertBox() using "info" state and "info-sign" icon
        
        :type message: basestr
        """
        return self.HtmlAlertBox(message, 'info', 'info-sign', closable)

    def HtmlAlertBoxWarning(self, message, closable = True):
        """Shortcut for HtmlAlertBox() using the default (yellow) state and
        "warning-sign" icon
        
        :type message: basestr
        """
        return self.HtmlAlertBox(message, '', 'warning-sign', closable)

    def HtmlAlertBoxError(self, message, closable = True):
        """Shortcut for HtmlAlertBox() using "error" state and "warning-sign" icon
        
        :type message: basestr
        """
        return self.HtmlAlertBox(message, 'error', 'warning-sign', closable)

    def Generate(self):
        """Renders the Session messages and then continues to Generate the HTML"""
        self._SessionMsgRender()
        return htmlwriter.HtmlWriterEx.Generate(self)

    if macho.mode == 'server':

        def HandleAction(self, action, request, response):
            self.request = request
            self.response = response
            if action is None:
                action = self.__defaultaction__
            if action in getattr(self, '__exporteddataactions__', {}):
                if request.query.has_key('act'):
                    act = request.QueryString('act')
                elif request.form.has_key('act'):
                    act = request.Form('act')
                else:
                    act = ''
                if act is None:
                    act = ''
                table = action
                if type(self.__exporteddataactions__[action]) == types.DictType and self.__exporteddataactions__[action].get('role', ROLE_ANY) & session.role == 0:
                    session.LogSessionError("Called %s::%s, which requires role 0x%x, which the user doesn't have" % (request.path, action, session.role))
                    self.CheckAuthorized(request, response, session, self.__exporteddataactions__[action].get('role', ROLE_ANY))
                    return
                params = self.__exporteddataactions__[action]
                if act == 'DataEdit':
                    self.DataEdit(request, response, table)
                elif act == 'DataEditSubmit':
                    self.DataEditSubmit(request, response, table)
                elif act == 'DataAdd':
                    self.DataAdd(request, response, table)
                elif act == 'DataAddSubmit':
                    self.DataAddSubmit(request, response, table)
                elif act == 'DataRemove':
                    self.DataRemove(request, response, table)
                elif act == 'DataRemoveSubmit':
                    self.DataRemoveSubmit(request, response, table)
                else:
                    self.DataView(request, response, table, params)
                self.inserts['title'] = str(action)
                self.inserts['heading'] = self.inserts['title']
            else:
                try:
                    htmlwriter.HtmlWriterEx.HandleAction(self, action, request, response)
                except RoleNotAssignedError as e:
                    self.CheckAuthorized(request, response, session, e.roles)

                if self.usePannelUpdate:
                    main = request.QueryString('_main')
                    if main:
                        self.inserts['onload'] = self.inserts['onload'] + "UpdateMainPannel('%s');\n" % main
                    search = request.QueryString('_search')
                    if search:
                        self.inserts['onload'] = self.inserts['onload'] + "UpdateSearchPannel('%s');\n" % search
                self.WritePolarisWarning()
            if self.cache.Setting('zsystem', 'SP-Log') == '1':
                dbzevent = self.DB2.GetSchema('zevent')
                stop, hz = blue.os.GetCycles()
                duration = int((stop - self.start) / float(hz) * 1000.0)
                nodeID = sm.GetService('machoNet').GetNodeID()
                args = request.QueryStrings()
                formData = request.form
                if hasattr(request, 'header'):
                    referer = request.header.get('Referer')
                    ipAddress = request.ep.address[:request.ep.address.find(':')]
                else:
                    import http
                    referer = http.Referer()
                    ipAddress = http.Host()
                args.pop('action', None)
                args.pop('', None)
                formData.pop('action', None)
                for key in formData.iterkeys():
                    if key is not None and 'password' in str(key).lower():
                        formData[key] = 'REMOVED'

                args = str(args) if len(args) > 0 else None
                formData = str(formData)[:4000] if len(formData) > 0 else None
                dbzevent.ServerPageEvents_Insert(duration, session.userid, ipAddress, nodeID, request.path, action, args, formData, referer)

        def DataColumnValue(self, column, value):
            if column.IS_NULLABLE == 1 and (value is None or value == '' or value == -1):
                return 'NULL'
            if column.DATA_TYPE in (58, 61, 167, 175, 231, 239):
                return "'" + unicode(value).replace("'", "''") + "'"
            if column.DATA_TYPE == 104:
                if value == 'on':
                    return '1'
                else:
                    return '0'
            else:
                if value is None or value == '':
                    return '0'
                return str(value)

        def DataColumns(self, table, view = '', columns = []):
            dbzsystem = self.DB2.GetSchema('zsystem')
            if view == '':
                crs = dbzsystem.DataColumns_Select(table, 1)
            else:
                crs = dbzsystem.DataColumns_Select(view, 0)
            rowDescriptor = blue.DBRowDescriptor((('COLUMN_NAME', const.DBTYPE_STR),
             ('DATA_TYPE', const.DBTYPE_UI1),
             ('CHAR_MAX_LEN', const.DBTYPE_I2),
             ('IS_NULLABLE', const.DBTYPE_BOOL),
             ('IS_IDENTITY', const.DBTYPE_BOOL),
             ('PK_ORDINAL', const.DBTYPE_I4),
             ('UK_ORDINAL', const.DBTYPE_I4)))
            ncrs = crowset.CRowset(rowDescriptor, [])
            for cr in crs:
                if columns == [] or cr.name in columns:
                    ncrs.InsertNew([str(cr.name),
                     cr.system_type_id,
                     cr.max_length,
                     cr.is_nullable,
                     cr.is_identity,
                     cr.is_primary_key,
                     None])

            if view != '':
                crs = dbzsystem.DataColumns_Select(table, 1)
                for cr in crs:
                    if cr.is_primary_key == 1:
                        for ncr in ncrs:
                            if ncr.COLUMN_NAME == cr.name:
                                ncr.PK_ORDINAL = 1

            return ncrs

        def DataView(self, request, response, table, params):
            self.WriteH2(table)
            view = ''
            where = ''
            columns = []
            order = ''
            actions = 'ERA'
            back = None
            top = ''
            where = request.QueryString('where')
            if where is None:
                whereString = ''
            else:
                whereString = 'WHERE ' + where
            if type(params) == types.DictType:
                if params.has_key('view'):
                    view = params['view']
                if params.has_key('columns'):
                    columns = params['columns']
                if params.has_key('order'):
                    order = ' ORDER BY ' + params['order']
                if params.has_key('actions'):
                    actions = params['actions']
                if params.has_key('back'):
                    back = params['back']
                if 'top' in params:
                    top = 'TOP %s ' % params['top']
            crs = self.DataColumns(table, view, columns)
            header = []
            select = ''
            for cr in crs:
                header.append(cr.COLUMN_NAME)
                if select != '':
                    select = select + ', '
                select = select + cr.COLUMN_NAME

            if view == '':
                rs = self.DB2.SQL('SELECT %s%s FROM %s %s %s' % (str(top),
                 str(select),
                 str(table),
                 str(whereString),
                 str(order)))
            else:
                rs = self.DB2.SQL('SELECT %s%s FROM %s %s %s' % (str(top),
                 str(select),
                 str(view),
                 str(whereString),
                 str(order)))
            lines = []
            act = ''
            if len(rs) > 0:
                for r in rs:
                    self.BeNice()
                    line = []
                    actEdit = {'action': table,
                     'act': 'DataEdit'}
                    actRemove = {'action': table,
                     'act': 'DataRemove'}
                    if where is not None:
                        actEdit['where'] = where
                        actRemove['where'] = where
                    if back is not None:
                        actEdit['back'] = back
                        actRemove['back'] = back
                    for cr in crs:
                        bon = ''
                        boff = ''
                        if cr.PK_ORDINAL > 0 or cr.UK_ORDINAL > 0:
                            bon = '<B>'
                            boff = '</B>'
                            actEdit[cr.COLUMN_NAME] = r[cr.COLUMN_NAME]
                            actRemove[cr.COLUMN_NAME] = r[cr.COLUMN_NAME]
                        if r[cr.COLUMN_NAME] is None:
                            line.append('')
                        elif cr.DATA_TYPE in (58, 61):
                            line.append(util.FmtDateEng(r[cr.COLUMN_NAME], 'ls'))
                        else:
                            line.append(bon + unicode(r[cr.COLUMN_NAME]) + boff)

                    act = ''
                    if 'E' in actions:
                        act = self.Link('', 'Edit', actEdit)
                    if 'R' in actions:
                        if act != '':
                            act = act + ', '
                        act = act + self.Link('', 'Remove', actRemove)
                    if act != '':
                        line.append(act)
                    lines.append(line)

            if act != '':
                header.append('act')
            customActions = None
            if 'A' in actions:
                customActions = [self.Button('', 'Add', {'action': table,
                  'act': 'DataAdd',
                  'where': where,
                  'back': back})]
            self.WriteTable(header, lines, useFilter=True, customActions=customActions)

        def DataEdit(self, request, response, table):
            self.WriteH2(table + ': EDIT')
            where = request.QueryString('where')
            back = request.QueryString('back')
            crs = self.DataColumns(table)
            sql = ''
            for cr in crs:
                if cr.PK_ORDINAL > 0 or cr.UK_ORDINAL > 0:
                    cv = request.QueryString(cr.COLUMN_NAME)
                    if sql != '':
                        sql = sql + ' AND'
                    dcv = self.DataColumnValue(cr, cv)
                    if cv is None and dcv == 'NULL':
                        op = 'IS'
                    else:
                        op = '='
                    sql = sql + ' %s %s %s' % (cr.COLUMN_NAME, op, dcv)

            sql = 'SELECT * FROM %s WHERE' % table + sql
            rs = self.DB2.SQL(sql)
            if len(rs) > 0:
                r = rs[0]
                form = htmlwriter.Form('', table, 'POST', request=request)
                form.AddHidden('act', 'DataEditSubmit')
                form.AddHidden('table', table)
                if where:
                    form.AddHidden('where', where)
                if back:
                    form.AddHidden('back', back)
                for cr in crs:
                    if cr.PK_ORDINAL > 0 or cr.UK_ORDINAL > 0:
                        form.AddHidden(cr.COLUMN_NAME, r[cr.COLUMN_NAME])
                        form.AddReadOnly(cr.COLUMN_NAME, '<b>' + str(r[cr.COLUMN_NAME]) + '</b>')
                    else:
                        cv = r[cr.COLUMN_NAME]
                        if cr.DATA_TYPE in (167, 231):
                            if int(cr.CHAR_MAX_LEN) < 0:
                                form.AddTextArea(cr.COLUMN_NAME, cv, 100, 20)
                            elif int(cr.CHAR_MAX_LEN) > 100:
                                lines = int(int(cr.CHAR_MAX_LEN) / 100)
                                if lines < 4:
                                    lines = 4
                                form.AddTextArea(cr.COLUMN_NAME, cv, 100, lines)
                            else:
                                ilen = int(cr.CHAR_MAX_LEN) + 5
                                if ilen > 70:
                                    ilen = 70
                                form.AddInput(cr.COLUMN_NAME, cv, ilen, '', None, 'maxlength=' + str(cr.CHAR_MAX_LEN))
                        elif cr.DATA_TYPE == 104:
                            form.AddCheckbox(cr.COLUMN_NAME, '', cv)
                        elif cr.DATA_TYPE in (58, 61):
                            if cv == '':
                                form.AddInput(cr.COLUMN_NAME, cv, 20)
                            else:
                                form.AddInput(cr.COLUMN_NAME, util.FmtDateEng(cv), 20)
                        else:
                            form.AddInput(cr.COLUMN_NAME, cv, 10)

                self.Write(form.AddSubmit(table, 'Submit'))
            else:
                self.Write('Record not found')

        def DataEditSubmit(self, request, response, table):
            crs = self.DataColumns(table)
            sql1 = ''
            sql2 = ''
            for cr in crs:
                cv = request.Form(cr.COLUMN_NAME)
                dcv = self.DataColumnValue(cr, cv)
                if cv is None and dcv == 'NULL':
                    op = 'IS'
                else:
                    op = '='
                if cr.PK_ORDINAL > 0 or cr.UK_ORDINAL > 0:
                    if sql2 != '':
                        sql2 = sql2 + ' AND'
                    sql2 = sql2 + ' %s %s %s' % (cr.COLUMN_NAME, op, dcv)
                else:
                    if sql1 != '':
                        sql1 = sql1 + ', '
                    sql1 = sql1 + cr.COLUMN_NAME + ' = ' + dcv

            sql = 'UPDATE %s SET %s WHERE %s' % (table, sql1, sql2)
            self.DB2.SQL(sql)
            where = request.Form('where')
            back = request.Form('back')
            ret = ''
            if back is None:
                ret = '?action=%s' % table
            else:
                ret = '?action=%s' % back
            if where is not None:
                ret = ret + '&where=' + where + '&'
            response.Redirect(ret)

        def DataAdd(self, request, response, table):
            self.WriteH2(table + ': ADD')
            where = request.QueryString('where')
            back = request.QueryString('back')
            crs = self.DataColumns(table)
            form = htmlwriter.Form('', table, 'POST', request=request)
            form.AddHidden('act', 'DataAddSubmit')
            form.AddHidden('table', table)
            if where:
                form.AddHidden('where', where)
            if back:
                form.AddHidden('back', back)
            for cr in crs:
                if cr.IS_IDENTITY == 0:
                    if cr.DATA_TYPE in (167, 231):
                        if int(cr.CHAR_MAX_LEN) < 0:
                            form.AddTextArea(cr.COLUMN_NAME, '', 100, 20)
                        elif int(cr.CHAR_MAX_LEN) > 100:
                            lines = int(int(cr.CHAR_MAX_LEN) / 100)
                            if lines < 4:
                                lines = 4
                            form.AddTextArea(cr.COLUMN_NAME, '', 100, lines)
                        else:
                            ilen = int(cr.CHAR_MAX_LEN) + 5
                            if ilen > 70:
                                ilen = 70
                            form.AddInput(cr.COLUMN_NAME, '', ilen, '', None, 'maxlength=' + str(cr.CHAR_MAX_LEN))
                    elif cr.DATA_TYPE == 104:
                        form.AddCheckbox(cr.COLUMN_NAME, '', 0)
                    else:
                        form.AddInput(cr.COLUMN_NAME, '', 10)

            self.Write(form.AddSubmit(table, 'Submit'))

        def DataAddSubmit(self, request, response, table):
            crs = self.DataColumns(table)
            sql1 = ''
            sql2 = ''
            for cr in crs:
                if cr.IS_IDENTITY == 0:
                    cv = request.Form(cr.COLUMN_NAME)
                    if sql1 != '':
                        sql1 = sql1 + ', '
                    sql1 = sql1 + cr.COLUMN_NAME
                    if sql2 != '':
                        sql2 = sql2 + ', '
                    sql2 = sql2 + self.DataColumnValue(cr, cv)

            sql = 'INSERT INTO %s (%s) VALUES (%s)' % (table, sql1, sql2)
            self.DB2.SQL(sql)
            where = request.Form('where')
            back = request.Form('back')
            ret = ''
            if back is None:
                ret = '?action=%s' % table
            else:
                ret = '?action=%s' % back
            if where is not None:
                ret = ret + '&where=' + where + '&'
            response.Redirect(ret)

        def DataRemove(self, request, response, table):
            self.WriteH2(table + ': REMOVE')
            where = request.QueryString('where')
            back = request.QueryString('back')
            crs = self.DataColumns(table)
            sql = ''
            for cr in crs:
                if cr.PK_ORDINAL > 0 or cr.UK_ORDINAL > 0:
                    cv = request.QueryString(cr.COLUMN_NAME)
                    if sql != '':
                        sql = sql + ' AND'
                    dcv = self.DataColumnValue(cr, cv)
                    if cv is None and dcv == 'NULL':
                        op = 'IS'
                    else:
                        op = '='
                    sql = sql + ' %s %s %s' % (cr.COLUMN_NAME, op, dcv)

            sql = 'SELECT * FROM %s WHERE' % table + sql
            rs = self.DB2.SQL(sql)
            if len(rs) > 0:
                r = rs[0]
                form = htmlwriter.Form('', table, request=request)
                form.AddHidden('act', 'DataRemoveSubmit')
                form.AddHidden('table', table)
                if where:
                    form.AddHidden('where', where)
                if back:
                    form.AddHidden('back', back)
                for cr in crs:
                    if cr.PK_ORDINAL > 0 or cr.UK_ORDINAL > 0:
                        form.AddHidden(cr.COLUMN_NAME, r[cr.COLUMN_NAME])
                        form.AddReadOnly(cr.COLUMN_NAME, '<b>' + str(r[cr.COLUMN_NAME]) + '</b>')
                    elif r[cr.COLUMN_NAME] is None:
                        form.AddReadOnly(cr.COLUMN_NAME, '')
                    else:
                        form.AddReadOnly(cr.COLUMN_NAME, unicode(r[cr.COLUMN_NAME]))

                self.Write(form.AddSubmit(table, 'Submit', '', 1))
            else:
                self.Write('Record not found')

        def DataRemoveSubmit(self, request, response, table):
            crs = self.DataColumns(table)
            sql = ''
            for cr in crs:
                cv = request.QueryString(cr.COLUMN_NAME)
                if cr.PK_ORDINAL > 0 or cr.UK_ORDINAL > 0:
                    if sql != '':
                        sql = sql + ' AND'
                    dcv = self.DataColumnValue(cr, cv)
                    if cv is None and dcv == 'NULL':
                        op = 'IS'
                    else:
                        op = '='
                    sql = sql + ' %s %s %s' % (cr.COLUMN_NAME, op, dcv)

            sql = 'DELETE FROM %s WHERE %s' % (table, sql)
            self.DB2.SQL(sql)
            where = request.QueryString('where')
            back = request.QueryString('back')
            ret = ''
            if back is None:
                ret = '?action=%s' % table
            else:
                ret = '?action=%s' % back
            if where is not None:
                ret = ret + '&where=' + where + '&'
            response.Redirect(ret)

        def WriteRow(self, r, hidden = [], dates = [], shortTimes = [], longTimes = [], userIDs = [], itemIDs = [], typeIDs = [], showCount = False, backLink = True):
            lines = []
            for h in r.__header__:
                c = h[0]
                v = r[c]
                if v is None:
                    v = ''
                elif h[1] == const.DBTYPE_FILETIME and c not in dates and c not in shortTimes and c not in longTimes:
                    v = util.FmtDateEng(v, 'ls')
                elif c in dates:
                    v = util.FmtDateEng(v, 'ln')
                elif c in shortTimes:
                    v = util.FmtDateEng(v, 'ls')
                elif c in longTimes:
                    v = util.FmtDateEng(v, 'll')
                elif c in userIDs:
                    v = self.UserLink(v, v)
                elif c in itemIDs:
                    v = self.ItemID(v)
                elif c in typeIDs:
                    v = self.TypeLink(v, v)
                lines.append([self.FontProperty(c), v])

            self.WriteTable(['Property', 'Value'], lines, showCount=showCount)
            if backLink:
                self.WriteRight(self.BackLink())

        def WriteRowset(self, rs, hidden = [], dates = [], shortTimes = [], longTimes = [], userIDs = [], showCount = True, useFilter = False, customActions = None, maxRows = None):
            lines = []
            header = []
            for h in rs.header:
                c = h[0]
                if c in hidden:
                    continue
                header.append(c)
                if h[1] == const.DBTYPE_FILETIME:
                    if c not in dates and c not in shortTimes and c not in longTimes:
                        shortTimes.append(c)

            for r in rs:
                self.BeNice()
                line = []
                for h in header:
                    if h in hidden:
                        continue
                    if r[h] is None:
                        line.append('')
                    else:
                        v = r[h]
                        if v is None:
                            v = ''
                        elif h in dates:
                            v = util.FmtDateEng(v, 'ln')
                        elif h in shortTimes:
                            v = util.FmtDateEng(v, 'ls')
                        elif h in longTimes:
                            v = util.FmtDateEng(v, 'll')
                        elif h in userIDs:
                            v = self.UserLink(v)
                        line.append(v)

                lines.append(line)

            self.WriteTable(header, lines, showCount=showCount, useFilter=useFilter, customActions=customActions, maxRows=maxRows)

        def WriteMetricGraph(self, counterID, columnID, subjectID, keyID, rows = 50, graph = 'area', width = 1000, height = 300, data = False):
            if rows > 5000:
                self.WriteError('Max 5000 rows supported')
                return
            c = self.cache.Index(const.cacheMetricCounters, counterID)
            if c.counterTable == 'zmetric.simpleCounters':
                rs = self.DB2.SQLInt('TOP %d counterDate, value' % rows, 'zmetric.simpleCounters', '', 'counterDate DESC', 'counterID', counterID)
            elif c.counterTable == 'zmetric.keyCounters':
                rs = self.DB2.SQLInt('TOP %d counterDate, value' % rows, 'zmetric.keyCounters', 'columnID = %d AND keyID = %d' % (columnID, keyID), 'counterDate DESC', 'counterID', counterID)
            elif c.counterTable == 'zmetric.keyTimeCounters':
                rs = self.DB2.SQLInt('TOP %d counterDate, value' % rows, 'zmetric.keyTimeCounters', 'columnID = %d AND keyID = %d' % (columnID, keyID), 'counterDate DESC', 'counterID', counterID)
            elif c.counterTable == 'zmetric.subjectKeyCounters':
                rs = self.DB2.SQLInt('TOP %d counterDate, value' % rows, 'zmetric.subjectKeyCounters', 'columnID = %d AND subjectID = %d AND keyID = %d' % (columnID, subjectID, keyID), 'counterDate DESC', 'counterID', counterID)
            else:
                self.WriteError('Counter type not supported')
                return
            dataHeader = [('string', 'Date'), ('number', 'Value')]
            dataLines = []
            for r in rs:
                dataLines.insert(0, [util.FmtDate(r.counterDate, 'ln'), r.value])

            if graph == 'line':
                self.WriteLineChart('Graph', dataHeader, dataLines, options={'width': width,
                 'height': height})
            elif graph == 'area':
                self.WriteAreaChart('Graph', dataHeader, dataLines, options={'width': width,
                 'height': height})
            elif graph == 'column':
                self.WriteColumnChart('Graph', dataHeader, dataLines, options={'width': width,
                 'height': height})
            else:
                self.WriteError('Graph type not supported')
                return
            if data:
                self.WriteRowset(rs)

        def MultiNotes(self, typeID, referenceID, title, redir, noteID = None, rows = 300):
            dbznote = self.DB2.GetSchema('znote')
            rs = dbznote.MultiNotes_SelectTop(typeID, referenceID, noteID, rows)
            lines = []
            for r in rs:
                self.BeNice()
                s = '%s - %s' % (util.FmtDateEng(r.noteDate, 'ss'), self.UserLink(r.userID))
                if session.role & ROLE_GMH and (r.userID is None or r.userID == session.userid):
                    s += self.MidDot()
                    s += self.Link('/note.py', 'Edit', {'action': 'MultiNoteEditForm',
                     'noteID': r.noteID,
                     'redir': redir})
                    s += ' / '
                    s += self.Link('/note.py', 'Remove', {'action': 'MultiNoteRemove',
                     'noteID': r.noteID,
                     'redir': redir}, '', None, 1)
                lines.append([self.FontGray(s)])
                lines.append([self.Font(htmlutils.parse_user_notes(r.note), size=2)])

            customActions = []
            if session.role & ROLE_GML or session.role & ROLE_GMH:
                customActions.append(self.Button('/note.py', 'Add Note', {'action': 'MultiNoteAddForm',
                 'typeID': typeID,
                 'referenceID': referenceID,
                 'redir': redir}))
            self.WriteTable([], lines, title=title, customActions=customActions, showCount=False)

        def ChangeID(self, changeID):
            return self.Link('/gd/bsd.py', changeID, {'action': 'Change',
             'changeID': changeID})

        def ChangeLink(self, r, colID = 'changeID', colDate = 'submitDate'):
            s = self.Link('/gd/bsd.py', 'CHANGE', {'action': 'Change',
             'changeID': r[colID]})
            if r[colDate] is None:
                s += self.FontBoldOrange(' (OPEN)')
            return s

        def RevisionID(self, revisionID):
            return self.Link('/gd/bsd.py', revisionID, {'action': 'Revision',
             'revisionID': revisionID})

        def RevisionDetailLink(self, r, role, oer = '', odr = ''):
            if session.role & role:
                if oer != '' and odr != '':
                    s = self.Link('/gd/bsd.py', 'DETAIL', {'action': 'RevisionDetail',
                     'revisionID': r.revisionID,
                     'oer': oer,
                     'odr': odr})
                elif oer != '':
                    s = self.Link('/gd/bsd.py', 'DETAIL', {'action': 'RevisionDetail',
                     'revisionID': r.revisionID,
                     'oer': oer})
                else:
                    s = self.Link('/gd/bsd.py', 'DETAIL', {'action': 'RevisionDetail',
                     'revisionID': r.revisionID})
                return s
            else:
                return ''

        def RevisionLink(self, r, colID = 'revisionID', colDate = 'submitDate'):
            s = self.Link('/gd/bsd.py', 'REVISION', {'action': 'Revision',
             'revisionID': r[colID]})
            if r[colDate] is None:
                s += self.FontBoldOrange(' (OPEN)')
            return s

        def RevisionLinks(self, r, role, oer = '', odr = ''):
            if r is None:
                return ''
            s = self.RevisionDetailLink(r, role, oer, odr)
            if s != '':
                s += self.MidDot()
            s += self.RevisionLink(r)
            return s

        def RevisionRowset(self, rs, schema, table, columns = [], addLink = 1, maxRows = 2000, role = ROLE_CONTENT):
            """
            Automatic revision rowset, with DETAIL, REVISION and ADD links
            table should not include Tx, it will be automatically added where needed
            """
            oer = self.request.path + '?' + self.request.args
            header = []
            for c in columns:
                header.append(c)

            header.append('act')
            lines = []
            for r in rs:
                self.BeNice()
                line = []
                for c in columns:
                    v = r[c]
                    if type(v) == types.BooleanType:
                        line.append([self.FontGray('0'), '1'][v])
                    else:
                        html = self.IsNone(r[c], '')
                        if isinstance(html, basestring) and html.startswith('res:'):
                            html = self.GetA(html, html)
                        line.append(html)

                line.append(self.RevisionLinks(r, role, oer))
                lines.append(line)

            customActions = []
            if addLink == 1:
                if session.role & role:
                    if table[-2:] == 'Ex':
                        table = table[:-2]
                    customActions.append(self.Button('/gd/bsd.py', 'ADD', {'action': 'RevisionAdd',
                     'schemaName': schema,
                     'tableName': table + 'Tx',
                     'oer': oer}))
            self.WriteTable(header, lines, useFilter=True, customActions=customActions)
            s = ''
            if len(lines) == maxRows:
                s = self.Space(5) + self.FontRed('ONLY TOP %s RECORDS ARE LISTED' % maxRows)
            self.WriteRight(s)

        def RevisionTable(self, schema, table, columns = [], where = '', order = '', addLink = 1, maxRows = 2000, role = ROLE_CONTENT):
            """
            Automatic revision table, with DETAIL, REVISION and ADD links
            table should not include Tx, it will be automatically added where needed
            """
            columnString = ''
            for c in columns:
                columnString += '%s, ' % c

            columnString += 'revisionID, submitDate'
            if where != '':
                where = ' WHERE ' + where
            if order != '':
                order = ' ORDER BY ' + order
            rs = self.DB2.SQL('SELECT TOP (%d) %s FROM %s.%s%s%s' % (maxRows,
             columnString,
             schema,
             table,
             where,
             order))
            self.RevisionRowset(rs, schema, table, columns, addLink, maxRows, role)

        def WriteOpenRevisionTable(self, tableID, linkPage = None, linkText = None, linkAction = None, linkID = None):
            """
            Write out a table listing all open revisions for a table
            tableID is either an int or a list with schema, table
            table should not include Tx, it will be automatically added where needed
            """
            if type(tableID) == types.ListType:
                schema = tableID[0]
                table = tableID[1] + 'Tx'
                tableID = self.cache.TableID(schema, table)
            rs = self.DB2.SQLInt('*', 'zstatic.revisionsEx', 'branchID = 1 AND submitDate IS NULL', 'changeID, revisionID', 'tableID', tableID)
            if len(rs) > 0:
                self.WriteH2(self.cache.SchemaTableName(tableID))
                lines = []
                for r in rs:
                    self.BeNice()
                    keyID = '%d' % r.keyID
                    if r.keyID2:
                        keyID += '-%d' % r.keyID2
                    link = ''
                    if linkPage:
                        link = self.Link(linkPage, linkText, {'action': linkAction,
                         linkID: r.keyID})
                    lines.append([self.RevisionID(r.revisionID),
                     util.FmtDateEng(r.revisionDate, 'ls'),
                     r.branchName,
                     keyID,
                     self.FontBold(r.revision),
                     r.action,
                     self.ChangeID(r.changeID),
                     r.changeText,
                     r.userName,
                     util.FmtDateEng(r.changeDate, 'ls'),
                     link])

                self.WriteTable(['revisionID',
                 'revisionDate',
                 'branchName',
                 'key',
                 'revision',
                 'action',
                 'changeID',
                 'changeText',
                 'userName',
                 'changeDate',
                 'act'], lines, useFilter=True)
            return len(rs)

        def WriteOpenRevisionSchema(self, schemaName, title = None):
            """
            For each table in a schema, write out a table listing all open revisions
            """
            schemaID = self.cache.SchemaID(schemaName)
            if title is None:
                title = schemaName
            self.WriteH1(self.FontOrange('OPEN REVISIONS - %s' % title))
            wroteSomething = False
            for t in self.cache.Rowset(const.cacheSystemTables):
                if t.schemaID == schemaID and t.tableName.endswith('Tx'):
                    self.BeNice()
                    if self.WriteOpenRevisionTable(t.tableID):
                        wroteSomething = True

            if not wroteSomething:
                self.WriteParagraph('No open revisions to display.')

        def WriteChangesNotTestedSchema(self, schemaName, releaseID, rows, submit, title = None, page = 'xChangesNotTested'):
            """
            Write a changes not tested form
            If submit=1 write out a changes not tested table
            """
            if title is None:
                title = schemaName
            self.WriteH1(self.FontOrange('CHANGES NOT TESTED - %s' % title))
            self.WriteBreak(2)
            releases = {}
            releases[None] = '(All releases except DEFERRED and IGNORE)'
            for r in self.BSD.Releases():
                releases[r.releaseID] = r.releaseName

            form = htmlwriter.Form('', page, request=self.request)
            form.AddSelect('releaseID', releases, None, releaseID)
            form.AddSelect('rows', self.ComboRows(), None, rows)
            form.AddHidden('submit', 1)
            self.Write(form.AddSubmit(page, 'SUBMIT'))
            if submit != 1:
                return
            if releaseID is None:
                w = ' C.releaseID > 0'
            else:
                w = ' C.releaseID = %d' % releaseID
            tables = ''
            schemaID = self.cache.SchemaID(schemaName)
            for t in self.cache.Rowset(const.cacheSystemTables):
                if t.schemaID == schemaID and t.tableName.endswith('Tx'):
                    tables = self.SplitAdd(tables, str(t.tableID), ', ')

            rs = self.DB2.SQL('\n                SELECT DISTINCT TOP %d C.*\n                  FROM zstatic.changes C\n                    INNER JOIN zstatic.revisions R ON R.changeID = C.changeID\n                 WHERE C.branchID = 1 AND C.testDate IS NULL AND C.submitDate IS NOT NULL AND %s AND R.tableID IN (%s)\n                 ORDER BY C.submitDate DESC, C.changeID DESC' % (rows, w, tables))
            lines = []
            for r in rs:
                self.BeNice()
                lines.append([self.ChangeID(r.changeID),
                 self.NiceText(r.changeText),
                 self.BSD.UserName(r.userID),
                 self.BSD.ReleaseName(r.releaseID),
                 self.FontBold(self.NoBreakDate(r.submitDate)),
                 self.ChangeLink(r)])

            self.WriteTable(['changeID',
             'changeText',
             'user',
             'release',
             'submitDate',
             'act'], lines)

        def WriteRevisionInfo(self, revisionID):
            r = self.BSD.RevisionInfo(revisionID)
            if r is None:
                return
            else:
                self.WriteDirect('rMenu', self.H2('Revision Info'))
                props = []
                props.append([self.FontProperty('branchName'), self.BSD.BranchName(r.branchID)])
                props.append([self.FontProperty('revisionDate'), util.FmtDateEng(r.revisionDate, 'ls')])
                props.append([self.FontProperty('revisionID'), self.RevisionID(r.revisionID)])
                props.append([self.FontProperty('dataID'), self.RevisionID(r.dataID)])
                if r.integrateID:
                    props.append([self.FontProperty('integrateID'), self.RevisionID(r.integrateID)])
                props.append([self.FontProperty('revision'), self.FontBold(r.revision)])
                props.append([self.FontProperty('action'), self.FontBold(self.BSD.RevisionAction(r.action, r.integrateID))])
                props.append([self.FontProperty('changeID'), self.ChangeID(r.changeID)])
                props.append([self.FontProperty('changeText'), r.changeText.replace('\n', '<br>')])
                props.append([self.FontProperty('userName'), self.BSD.UserName(r.userID)])
                props.append([self.FontProperty('changeDate'), util.FmtDateEng(r.changeDate, 'ls')])
                if r.submitDate is None:
                    props.append([self.FontProperty('submitDate'), self.FontBoldOrange('NOT SUBMITTED')])
                else:
                    props.append([self.FontProperty('submitDate'), self.FontBold(util.FmtDateEng(r.submitDate, 'ls'))])
                self.WriteDirect('rMenu', self.GetTable([], props, showCount=False))
                return r

        def WriteDiffTable(self, diffList):
            unchangedRevisions = []
            revisionCount = len(diffList)
            if revisionCount > 0:
                showDiff = 2
                if revisionCount > 5000:
                    showDiff = 0
                    self.Write(self.FontBoldRed('Change contains over 5,000 revisions, revision info and DIFF only shown for NO CHANGE revisions'))
                    self.WriteBreak(2)
                elif diffList[0][1] != 'DEV' and revisionCount > 100:
                    showDiff = 1
                    self.Write(self.FontBoldRed('Change not from DEV and contains over 100 revisions, revision info shown for all revisions, DIFF only shown for NO CHANGE revisions'))
                    self.WriteBreak(2)
                for line in diffList:
                    self.BeNice()
                    revisionID = line[0]
                    branchName = line[1]
                    tableName = line[2]
                    key = line[3]
                    revisionText = line[4]
                    revision = line[5]
                    actionText = line[6]
                    differences = line[7]
                    if showDiff or len(differences) == 0:
                        s = self.Font('%s: %s, %s, %s, %s, %s, %s' % (self.Link('/gd/bsd.py', revisionID, {'action': 'Revision',
                          'revisionID': revisionID}),
                         branchName,
                         tableName,
                         key,
                         htmlwriter.HTMLEncode(revisionText),
                         self.FontBold(revision),
                         self.FontBold(actionText)), size=2)
                        if len(differences) == 0:
                            s += ' - ' + self.FontBoldRed('NO CHANGE IN REVISION')
                            unchangedRevisions.append(revisionID)
                        self.WriteBreak()
                        self.Write(s)
                        if showDiff == 2 or len(differences) == 0:
                            lines = []
                            if actionText.endswith('Add'):
                                for d in differences:
                                    dColumn = d[0]
                                    dNewValue = d[2]
                                    lines.append([self.FontProperty(dColumn), dNewValue])

                            else:
                                for d in differences:
                                    dColumn = d[0]
                                    dOldValue = d[1]
                                    dNewValue = d[2]
                                    lines.append([self.FontProperty(dColumn), htmlwriter.HTMLEncode(dOldValue), htmlwriter.HTMLEncode(dNewValue)])

                            if len(lines) == 0:
                                self.WriteSplit()
                            else:
                                self.WriteTable([], lines, showCount=False)
                        else:
                            self.WriteSplit()

            return unchangedRevisions

        def WriteRelationUsage(self, text, schemaName, tableName, deleteID, rows = 3):
            lines = self.BSD.RelationUsageList(schemaName, tableName, deleteID, rows)
            if lines is None:
                return 0
            else:
                if text != '':
                    self.WriteH2(self.FontRed(text))
                self.WriteTable(['table',
                 'column',
                 'ID',
                 'key',
                 'keyID',
                 'keyText',
                 'link'], lines)
                self.WriteRight(self.FontGray('Note that only top %s rows are listed for each table') % rows)
                return 1

        def ReleaseName(self, releaseID):
            releaseName = self.BSD.ReleaseName(releaseID)
            if releaseID < 0:
                releaseName = self.FontGray(releaseName)
            elif releaseID > 0:
                releaseName = self.FontGreen(releaseName)
            return releaseName

        def SubmitDate(self, row):
            if row.submitDate is None:
                return self.FontBoldOrange(self.NoBreak('NOT SUBMITTED'))
            else:
                return self.FontBold(self.NoBreakDate(row.submitDate))

        def TestDate(self, row, userInfo = 0):
            if row.testDate is None:
                return ''
            else:
                s = self.FontBold(self.FontGreen(self.NoBreakDate(row.testDate)))
                if userInfo == 1:
                    if row.testUserID:
                        s += ', ' + self.FontBold(self.BSD.UserName(row.testUserID))
                return s

        def RevisionHistoryColors(self):
            return ['#ff9900',
             '#66ff66',
             '#ffff33',
             '#9999ff',
             '#ff66ff',
             '#00ccff',
             '#cccc33',
             '#00cccc',
             '#ffcc99',
             '#ccffff',
             '#ccccff',
             '#cccc99',
             '#99ccff',
             '#ccffcc',
             '#ffcccc',
             '#ffffcc']

        def WriteRevisionHistory(self, rev, rs = None, branchID = None):
            self.Write('<table border="0" width="100%%">')
            self.Write('<tr style="background-color: #e0e0e0">')
            self.Write('<td><b>%s</b>' % 'revisionID')
            self.Write('<td><b>dataID</b>')
            self.Write('<td><b>%s</b>' % 'integrateID')
            self.Write('<td><b>branch</b>')
            self.Write('<td><b>revision</b>')
            self.Write('<td><b>action</b>')
            self.Write('<td><b>changeID</b>')
            self.Write('<td><b>%s</b>' % 'changeText')
            self.Write('<td><b>user</b>')
            self.Write('<td><b>release</b>')
            self.Write('<td><b>%s</b>' % 'submitDate')
            self.Write('<td><b>testDate</b>')
            self.Write('</tr>')
            if rs is None:
                rs = self.BSD.RevisionHistory(branchID, rev.tableID, rev.keyID, rev.keyID2, rev.keyID3)
            colors = self.RevisionHistoryColors()
            dataColors = {}
            l = len(rs)
            for x in range(1, l + 1):
                r = rs[l - x]
                dataID = r.dataID
                if r.action == 'D':
                    dataID = -dataID
                if dataID not in dataColors:
                    if len(colors) == 0:
                        colors = self.RevisionHistoryColors()
                    dataColors[dataID] = colors.pop()

            if branchID is not None:
                b = self.BSD.Branch(branchID)
                indent = self.Space(b.indent)
            for r in rs:
                dataID = r.dataID
                if r.action == 'D':
                    dataID = -dataID
                color = dataColors[dataID]
                if r.revisionID == rev.revisionID:
                    revID = self.Link('/gd/bsd.py', self.FontBold(r.revisionID), {'action': 'Revision',
                     'revisionID': r.revisionID})
                else:
                    revID = self.RevisionID(r.revisionID)
                if branchID is None:
                    b = self.BSD.Branch(r.branchID)
                    indent = self.Space(b.indent)
                self.Write('<tr style="background-color: %s">' % color)
                self.Write('<td>%s' % revID)
                self.Write('<td>%s' % r.dataID)
                self.Write('<td>%s' % self.IsNone(r.integrateID, ''))
                self.Write('<td>%s' % indent + b.branchName)
                self.Write('<td>%s' % indent + self.FontBold(r.revision))
                self.Write('<td>%s' % indent + self.FontBold(self.BSD.RevisionAction(r.action, r.integrateID)))
                self.Write('<td>%s' % self.ChangeID(r.changeID))
                self.Write('<td>%s' % self.NiceText(r.changeText))
                self.Write('<td>%s' % self.BSD.UserName(r.userID))
                self.Write('<td>%s' % self.ReleaseName(r.releaseID))
                self.Write('<td>%s' % self.SubmitDate(r))
                self.Write('<td>%s' % self.TestDate(r))
                self.Write('</tr>')

            self.Write('</table>')

        def WritePickerJScript(self, functionName, fileName, columnName = None):
            if columnName:
                self.WriteScript("\n                    function %s()\n                    {\n                        pick = window.open('%s?columnName=%s','pick','toolbar=0,location=0,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=640,height=480');\n                    }\n                    " % (functionName, fileName, columnName))
            else:
                self.WriteScript("\n                    function %s()\n                    {\n                        pick = window.open('%s','pick','toolbar=0,location=0,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=640,height=480');\n                    }\n                    " % (functionName, fileName))

        def ESPLink(self, nodeID):
            """
                Constructs a base URL to the ESP of a particular node.
            """
            from http import ESPUrl
            return ESPUrl(self.session, nodeID)

        def HeaderLinksAdd(self, links, caller, linkText, linkAction, linkAttribute, linkID):
            links += '&nbsp;' * 8
            if caller == linkText:
                links += '<b>'
            links += self.Link('', linkText, {'action': linkAction,
             linkAttribute: linkID})
            if caller == linkText:
                links += '</b>'
            return links

        def SubjectHeader(self, small = 1, subjectTitle = 'SUBJECT', subjectID = 0, subjectName = '', bgcolor = '#FFFFE0', image = '', page = '', action = '', actionID = '', propertyValueList = [], siWidth = 80, siHeight = 80, fiWidth = 128, fiHeight = 128, tfSize = 4, tooltip = ''):
            if small == 1:
                width = siWidth
                height = siHeight
            else:
                width = fiWidth
                height = fiHeight
            image = self.Image(image, 'width=%d height=%d title="%s"' % (width, height, tooltip))
            if small == 1 and page != '':
                image = self.Link(page, image, {'action': action,
                 actionID: subjectID})
            layout = '' + '<table border=0 cellpadding=4 cellspacing=0 width=100% style="border:1px solid #A0A0A0;"><tr><td colspan=2 style="height:10px; font-size:3px; border-bottom:1px solid #A0A0A0; background-color:' + bgcolor + '">&nbsp;</td></tr>' + '<tr>' + '<td width=%s height=%s>%s</td>' % (width, height, image) + '<td valign=top>' + '<table border=0 cellpadding=0 cellspacing=0 width=100%>' + '<tr>' + '<td valign="top">' + '<table cellpadding=4 cellspacing=0 width="100%">' + '<tr>' + '<td width=84>' + self.FontHeaderProperty(subjectTitle) + '</td>' + '<td><font size=' + str(tfSize) + ' color=black><b>' + unicode(subjectName) + '</b></font></td>' + '<td width=96 align=right><b>' + unicode(subjectID) + '</b></td>' + '</tr>'
            for inSmall, property, value in propertyValueList:
                if small == 0 or small == 1 and inSmall == 1:
                    layout += '<tr><td width=84>' + self.FontHeaderProperty(property) + '</td>' + '<td>' + unicode(value) + '</td>' + '</tr>'

            layout += '</table></td></tr>' + '</table>' + '</td>' + '</tr>' + '</table>'
            self.Write(layout)

        def SubjectActions(self, lines, placement = 'rMenu'):
            layout = ['<div class="menu-sub">']
            for x in lines:
                if '&middot;' in x and x[0] not in ('>', '&gt;'):
                    x = '<span class="menu-block-s">%s</span>' % x
                if len(x) > 0 and x[0] in ('#', '>', '!', '-'):
                    if x[0] == '#':
                        layout.append('<div class="menu-header">%s</div>' % x[1:])
                    if x[0] == '-':
                        layout.append('<div class="menu-sep"></div>')
                    elif x[0] in ('>', '!'):
                        layout.append('<span class="menu-block">%s</span>' % x[1:])
                else:
                    layout.append(x)

            layout.append('</div>')
            self.WriteDirect(placement, ''.join(layout))

        def AppBeforeActions(self, coreStatic, appStatic, menuPlacement):
            pass

        def AppActions(self, coreStatic, appStatic, menuPlacement):
            pass

        def AppHeaderLines(self, coreStatic, appStatic):
            return []

        def AppInfoLines(self, coreStatic, appStatic, coreDynamic, appDynamic):
            return []

        def AppAfterHeader(self, coreStatic, appStatic, coreDynamic, appDynamic):
            pass

        def AppAfterInfo(self, coreStatic, appStatic, coreDynamic, appDynamic):
            pass

        def GetPickerUser(self, ctrlID, ctrlLabel = None, minLength = 3):
            if ctrlLabel is not None:
                ctrlLabel = self.HTMLEncode(ctrlLabel)
            return self.GetAutoComplete(ctrlID, ctrlLabel, callbackPy='/ds/userds.py', minLength=minLength)

        def UserHeader(self, userID, small = 1, menuPlacement = 'rMenu'):
            if userID < 1:
                self.WriteError('INVALID USERID SPECIFIED')
                return
            coreStatic, appStatic = self.cache.UserDataset(userID)
            if coreStatic is None:
                self.WriteError('USER NOT FOUND')
                return
            image = '/img/flags/48x48/flag_unknown.png'
            tooltip = ''
            if coreStatic.countryID:
                countryName = self.cache.IndexText(const.cacheUserCountries, coreStatic.countryID)
                if countryName:
                    image = '/img/flags/48x48/flag_%s.png' % countryName.lower().replace(' ', '_')
                    tooltip = countryName
            lines = []
            lines.append([1, 'Name', self.Font(coreStatic.fullName, size=3)])
            info = ''
            if coreStatic.countryID is not None:
                info = self.SplitAdd(info, self.cache.IndexText(const.cacheUserCountries, coreStatic.countryID), ', ')
            if coreStatic.gender is not None:
                info = self.SplitAdd(info, ['Female', 'Male'][coreStatic.gender], ', ')
            if coreStatic.dob is not None:
                info = self.SplitAdd(info, util.FmtDateEng(coreStatic.dob, 'ls'), ', ')
            lines.append([1, 'Info', info])
            for i in self.AppHeaderLines(coreStatic, appStatic):
                lines.append(i)

            self.SubjectHeader(small, 'USER', userID, coreStatic.userName, '#FFD0D0', image, '/gm/users.py', 'User', 'userID', lines, 48, 48, 48, 48, tooltip=tooltip)
            self.AppBeforeActions(coreStatic, appStatic, menuPlacement)
            lines = []
            lines.append('#USER')
            lines.append(self.Link('/gm/users.py', 'INFO', {'action': 'User',
             'userID': userID}))
            lines.append('-')
            if session.role & ROLE_ADMIN:
                lines.append(self.Link('/gm/users.py', 'Type', {'action': 'EditTypeForm',
                 'userID': userID}) + self.MidDot() + self.Link('/gm/users.py', 'Status', {'action': 'EditStatusForm',
                 'userID': userID}) + self.MidDot() + self.Link('/gm/users.py', 'Voice', {'action': 'EditVoiceForm',
                 'userID': userID}))
            lines.append(self.Link('/gm/users.py', 'Edit', {'action': 'EditUserForm',
             'userID': userID}))
            lines.append(self.Link('/gm/users.py', 'Password', {'action': 'EditPasswordForm',
             'userID': userID}) + self.MidDot() + self.Link('/gm/users.py', 'Master Password', {'action': 'MasterPassword',
             'userID': userID}))
            lines.append(self.Link('/gm/users.py', 'Roles', {'action': 'UserRoles',
             'userID': userID}))
            lines.append(self.Link('/gm/users.py', 'Notes', {'action': 'Notes',
             'userID': userID}))
            lines.append(self.Link('/gm/users.py', 'Computer and Settings', {'action': 'ComputerAndSettings',
             'userID': userID}))
            lines.append(self.Link('/gm/users.py', 'Overview Profiles Added', {'action': 'OverviewSettings',
             'userID': userID}))
            lines.append(self.Link('/gm/users.py', 'IP addresses', {'action': 'IpAddresses',
             'userID': userID}))
            lines.append('-')
            lines.append(self.Link('/gm/users.py', 'Role Events', {'action': 'RoleEvents',
             'userID': userID}))
            lines.append(self.Link('/gm/users.py', 'Connect Events', {'action': 'ConnectEvents',
             'userID': userID}))
            lines.append(self.Link('/gm/users.py', 'User Events', {'action': 'UserEvents',
             'userID': userID}))
            lines.append(self.Link('/gm/users.py', 'Connect and User Events', {'action': 'ConnectAndUserEvents',
             'userID': userID}))
            lines.append('-')
            lines.append(self.Link('/gm/users.py', 'Characters', {'action': 'Characters',
             'userID': userID}) + self.MidDot() + self.Link('/gm/users.py', 'Deleted Characters', {'action': 'DeletedCharacters',
             'userID': userID}))
            lines.append(self.Link('/gm/users.py', 'Cohorts', {'action': 'CohortsForUser',
             'userID': userID}))
            if session.role & ROLE_GMH:
                lines.append(self.Link('/gm/users.py', 'CREATE CHARACTER', {'action': 'CreateCharacterForm',
                 'userID': userID}))
            self.SubjectActions(lines, menuPlacement)
            self.WriteDirect(menuPlacement, self.Break())
            self.AppActions(coreStatic, appStatic, menuPlacement)

        def UserName(self, userID, valueIfNotExists = '???'):
            if userID is None:
                return
            r = self.cache.UserCoreRow(userID)
            if r is None:
                return valueIfNotExists
            return r.userName

        def UserLink(self, userID, linkText = None, props = '', noHover = False):
            if userID is None:
                return ''
            if linkText is None:
                linkText = self.UserName(userID)
                if linkText is None:
                    return self.GetSpan(['Unknown'], className='red')
            href = '/gm/users.py?action=User&userID=%s' % userID
            if linkText is not None:
                linkText = htmlwriter.HTMLEncode(linkText)
            if noHover:
                return self.GetA(innerText=linkText, href=href)
            return self.GetTooltip(href=href, ajax='/gm/worker_info.py?action=FetchInfo&id=%s&idType=2' % userID, title=linkText, caption=linkText)

        def UserTags(self, userID):
            rs = self.DB2.GetSchema('zuser').UserTags_Select(userID)
            s = ''
            for r in rs:
                if s != '':
                    s += self.MidDot(4)
                s += self.FontBoldOrange(self.cache.Dict(const.cacheUserTags)[r.tagID], size=3)
                s += ' ' + self.Link('/gm/users.py?action=RemoveUserTag&userID=%s&tagID=%s' % (userID, r.tagID), '[x]')

            if session.role & ROLE_GML:
                s += self.Space(10)
                s += self.Button('/gm/users.py', 'Add Tag', {'action': 'AddUserTag',
                 'userID': userID})
            self.WriteRight(s)

        def UserRedirect(self, userID, action = 'User'):
            self.response.Redirect('/gm/users.py?action=%s&userID=%d' % (action, userID))

        def CountryFlag(self, countryName, flagSize = '16', tooltip = 1):
            if not countryName:
                tooltipText = ''
                countryName = 'unknown'
            else:
                tooltipText = countryName
                countryName = countryName.lower().replace(' ', '_')
            props = 'border=0 align=absmiddle'
            if tooltip == 1:
                props += ' title="%s"' % tooltipText
            return self.Image('/img/flags/%(s)sx%(s)s/flag_%(c)s.png' % {'s': flagSize,
             'c': countryName}, props)

        def AppCharacterImage(self, coreStatic, appStatic):
            if coreStatic.gender is None:
                return '/img/character.jpg'
            else:
                return '/img/character_%s.jpg' % ['female', 'male'][coreStatic.gender]

        def AppUserCharactersInfo(self, coreStatic, appStatic):
            return self.GenderText(coreStatic.gender)

        def AppUserCharactersLocation(self, coreStatic, appStatic):
            return ''

        def AppUserCharactersAct(self, coreStatic, appStatic):
            return ''

        def AppGetAwayStatusTextForCharacter(self, characterID):
            return ''

        def FSDField(self, field):
            """
            This method adds an image denoting that this field is populated from FSD
            It also adds a link around the image pointing to the FSD wiki
            """
            return "<span>%s</span> <a href='http://carbon/wiki/FSD' >                            <img src='/img/FSDIcon.png' title='This data is coming from FSD and should be authored there' height='16px' width='16px'/>                            </a>" % field

        def TransitionFSDField(self, field, releaseUsingBSD, dataComingFromBSD = False):
            """
            This method adds an image denoting that this field is populated from FSD
            Although this can still be authored in BSD for emergency fixes
            It also adds a link around the image pointing to the FSD wiki
            """
            dataSource = 'FSD'
            if dataComingFromBSD:
                dataSource = 'BSD'
            tooltip = 'This field is in a transitional state where ' + releaseUsingBSD + ' is using BSD values, ' + 'but releases after ' + releaseUsingBSD + ' will use FSD values. ' + 'This value is currently coming from ' + dataSource
            return field + " <a href='http://carbon/wiki/FSD'> " + "<img src='/img/TransitionFSDIcon.png' title='" + tooltip + "' height='18px' width='18px'/>" + '</a>'

        def ResourceFile(self, resourceFile):
            if resourceFile is None:
                return ''
            if resourceFile.startswith('res:'):
                return self.GetA(resourceFile, resourceFile)
            return resourceFile

        def GraphicID(self, graphicID):
            if graphicID is None:
                return ''
            return self.Link('/gd/res2.py', graphicID, {'action': 'Graphic',
             'graphicID': graphicID})

        def GraphicLink(self, graphicID, linkText = None, action = 'Graphic'):
            if graphicID is None:
                return ''
            else:
                if linkText is None:
                    linkText = self.cache.IndexText(const.cacheResGraphics, graphicID)
                if action == 'Graphic':
                    return self.Link('/gd/res2.py', linkText, {'action': 'Graphic',
                     'graphicID': graphicID})
                return self.Link('/gd/res.py', linkText, {'action': action,
                 'graphicID': graphicID})

        def IconID(self, iconID):
            if iconID is None:
                return ''
            return self.Link('/gd/res2.py', iconID, {'action': 'Icon',
             'iconID': iconID})

        def IconLink(self, iconID, linkText = None, action = 'Icon'):
            if iconID is None:
                return ''
            else:
                if linkText is None:
                    linkText = self.cache.IndexText(const.cacheResIcons, iconID)
                if action == 'Icon':
                    return self.Link('/gd/res2.py', linkText, {'action': 'Icon',
                     'iconID': iconID})
                return self.Link('/gd/res.py', linkText, {'action': action,
                 'iconID': iconID})

        def CategoryLink(self, categoryID, linkText = None, action = 'Category', props = ''):
            if categoryID is None:
                return ''
            if linkText is None:
                linkText = self.SP.CategoryName(categoryID)
            return self.Link(self.SP.TypePage(), linkText, {'action': action,
             'categoryID': categoryID}, props)

        def GroupLink(self, groupID, linkText = None, action = 'Group', props = ''):
            if groupID is None:
                return ''
            if linkText is None:
                linkText = self.SP.GroupName(groupID)
            return self.Link(self.SP.TypePage(), linkText, {'action': action,
             'groupID': groupID}, props)

        def TypeLink(self, typeID, linkText = None, action = 'Type', props = ''):
            if typeID is None:
                return ''
            if linkText is None:
                linkText = self.SP.TypeName(typeID)
            return self.Link(self.SP.TypePage(), linkText, {'action': action,
             'typeID': typeID}, props)

        def ItemID(self, itemID, linkText = None, props = ''):
            if itemID is None:
                return ''
            if linkText is None:
                linkText = itemID
            return self.Link(self.SP.ItemPage(), linkText, {'action': 'Item',
             'itemID': itemID}, props)

        def ItemName(self, itemID):
            return self.SP.ItemName()

        def OwnerName(self, ownerID):
            return self.SP.OwnerName(ownerID)

        def OwnerLink(self, ownerID, linkText = None):
            if linkText is not None:
                return linkText
            return self.OwnerName(ownerID)

        def IPAddress(self, ipAddress, ipAddressID = None, ipAddressCountryID = None):
            s = self.CountryFlag(self.cache.IndexText(const.cacheUserCountries, ipAddressCountryID))
            s += ' '
            if ipAddressID:
                s += self.Link('/gm/users.py', ipAddress, {'action': 'IPLogs',
                 'IPID': ipAddressID})
            elif ipAddress:
                s += self.Link('/gm/users.py', ipAddress, {'action': 'IPLogs',
                 'IP': ipAddress})
            return s

        def OwnerMaxDate(self, ownerID, maxDate):
            """
            Get maxDate from session if not set
            The OwnerMaxDates dict stores a maxDate per ownerID if maxDate used on page
            """
            if maxDate is not None:
                maxDate = maxDate.split(' ')[0]
            if 'OwnerMaxDates' in session.esps.contents:
                d = session.esps.contents['OwnerMaxDates']
            else:
                d = {}
                session.esps.contents['OwnerMaxDates'] = d
            if maxDate == '':
                if ownerID in d:
                    del d[ownerID]
            elif maxDate is not None:
                d[ownerID] = maxDate
            elif ownerID in d:
                maxDate = d[ownerID]
            return maxDate

        def LocationName(self, locationID):
            return self.SP.LocationName(locationID)

        def LocationLink(self, locationID, linkText = None):
            if linkText is not None:
                return linkText
            return self.LocationName(locationID)

        def MessageLink(self, messageID, linkText = None):
            if linkText is None:
                linkText = str(messageID)
            return '<a href="/localization/localizationbrowser.py#/m:%s">%s</a>' % (linkText, str(messageID))

        def CharacterHeader(self, characterID, small = 1, menuPlacement = 'rMenu'):
            coreStatic, appStatic = self.cache.CharacterDataset(characterID)
            if coreStatic is None:
                self.WriteError('CHARACTER NOT FOUND')
                return
            image = self.AppCharacterImage(coreStatic, appStatic)
            info = ''
            if coreStatic.gender is not None:
                info = self.SplitAdd(info, self.GenderText(coreStatic.gender), ', ')
            lines = []
            if coreStatic.deleteDate:
                lines.append([1, '', self.FontBoldRed('CHARACTER HAS BEEN REMOVED', size=2)])
            elif coreStatic.deletePrepareDate:
                lines.append([1, '', self.FontBoldPurple('CHARACTER HAS BEEN PREPARED FOR REMOVE', size=2)])
            for i in self.AppHeaderLines(coreStatic, appStatic):
                lines.append(i)

            lines.append([1, 'User', self.Font(self.UserLink(coreStatic.userID), size=3)])
            self.SubjectHeader(small, 'CHARACTER', characterID, coreStatic.characterName, '#D0FFD0', image, '/gm/character.py', 'Character', 'characterID', lines)
            self.AppBeforeActions(coreStatic, appStatic, menuPlacement)
            lines = []
            lines.append('#CHARACTER')
            lines.append(self.Link('/gm/character.py', 'INFO', {'action': 'Character',
             'characterID': characterID}))
            lines.append('-')
            lines.append(self.Link('/gm/character.py', 'Bio', {'action': 'EditBioForm',
             'characterID': characterID}))
            if hasattr(util, 'hook_AppSpGmCharacterEvents'):
                lines.append(self.Link('/gm/events.py', 'Events', {'action': 'Events',
                 'pageType': 'CHARACTER',
                 'keyID': characterID}))
            self.SubjectActions(lines, menuPlacement)
            self.WriteDirect(menuPlacement, self.Break())
            self.AppActions(coreStatic, appStatic, menuPlacement)

        def CharacterName(self, characterID):
            if characterID is not None:
                coreStatic = self.cache.CharacterCoreRow(characterID)
                if coreStatic is not None:
                    return coreStatic.characterName

        def CharacterLink(self, characterID, linkText = None, props = ''):
            if characterID is None:
                return ''
            else:
                if linkText is None:
                    linkText = self.CharacterName(characterID)
                    if linkText is None:
                        return self.FontRed('???')
                if linkText is not None:
                    linkText = htmlwriter.HTMLEncode(linkText)
                return self.Link('/gm/character.py', linkText, {'action': 'Character',
                 'characterID': characterID}, props)

        def CharacterRedirect(self, characterID, action = 'Character'):
            self.response.Redirect('/gm/character.py?action=%s&characterID=%d' % (action, characterID))

        def WriteUserCharacters(self, userID, rMenuText = 0):
            layout = '<table bgcolor=#D0FFD0 border=0 cellpadding=4 cellspacing=0 width=100% style="border:1px solid #A0A0A0;">'
            layout += '<tr bgcolor=#D0D0D0>'
            layout += '<td><b>Portrait</b></td>'
            layout += '<td><b>Info</b><br>'
            layout += '<td><b>Location</b></td>'
            layout += '<td><b>act</b></td>'
            layout += '</tr>'
            d = self.SP.UserCharactersDict(userID)
            for characterID, rowList in d.iteritems():
                coreStatic, appStatic = rowList
                image = self.Link('/gm/character.py', self.Image(self.AppCharacterImage(coreStatic, appStatic), 'width=100 height=100'), {'action': 'Character',
                 'characterID': characterID})
                info = self.ItemID(characterID) + '<br><b><font size=2>' + coreStatic.characterName + '</font></b><br>'
                if coreStatic.deletePrepareDate:
                    info += self.FontBoldPurple('PREPARED FOR REMOVE<br>')
                info += self.AppUserCharactersInfo(coreStatic, appStatic)
                act = self.Link('/gm/character.py', 'VIEW', {'action': 'Character',
                 'characterID': characterID})
                act += self.AppUserCharactersAct(coreStatic, appStatic)
                layout += '<tr bgcolor=#C0C0C0 height=1><td></td><td></td><td></td><td></td></tr>'
                layout += '<tr valign=top>'
                layout += '<td width=96>' + image + '</td>'
                layout += '<td>' + info + '</td>'
                layout += '<td>' + self.AppUserCharactersLocation(coreStatic, appStatic) + '</td>'
                layout += '<td>' + act + '</td>'
                layout += '</tr>'

            layout += '</tr></table>'
            self.Write(layout)
            if rMenuText:
                ex = []
                u = self.cache.UserCoreRow(userID)
                ex.append('%s: %s' % (self.FontProperty('User'), u.userName))
                s = ''
                for characterID, rowList in d.iteritems():
                    coreStatic, appStatic = rowList
                    s += ', ' + coreStatic.characterName

                if s != '':
                    ex.append('%s%s: %s' % (self.Break(), self.FontProperty('Characters'), s[2:]))
                ex.append('%s%s: %s' % (self.Break(), self.FontProperty('Email'), u.eMail))
                self.WriteDirect('rMenu', self.Break())
                self.SubjectActions(ex, 'rMenu')
            return len(d)

        def ItemTypeAndName(self, row):
            typeName = '???'
            groupName = '???'
            categoryName = '???'
            typeRow = self.SP.TypeRow(row.typeID)
            if typeRow:
                typeName = typeRow.typeName
                groupRow = self.SP.GroupRow(typeRow.groupID)
                groupName = groupRow.groupName
                categoryName = self.SP.CategoryName(groupRow.categoryID)
            itemName = self.SP.ItemName(row.itemID)
            if itemName != '':
                itemName = ': ' + self.FontBold(itemName)
            return '%s: %s, %s, %s%s' % (row.typeID,
             categoryName,
             groupName,
             typeName,
             itemName)

        def ItemOwner(self, row):
            ownerName = self.SP.OwnerName(row.ownerID)
            if ownerName != '':
                ownerName = ': ' + ownerName
            return '%s%s' % (self.ItemID(row.ownerID), ownerName)

        def ItemLocation(self, row):
            locationName = self.SP.LocationName(row.locationID)
            if locationName != '':
                locationName = ': ' + locationName
            return '%s%s' % (self.ItemID(row.locationID), locationName)

        def ItemFlag(self, row):
            return '%s: %s' % (row.flagID, self.cache.IndexText(const.cacheInventoryFlags, row.flagID))

        def ItemAttributes(self, row):
            if row.quantity < 0:
                if row.quantity == -1:
                    return 'S'
                else:
                    return 'S' + self.FontRed(row.quantity)
            else:
                return row.quantity

        def ItemsOwnerTable(self, ownerID, lastLocationID = None, lastItemID = None, rows = 200, action = 'ItemsOwner'):
            dbzinventory = self.DB2.GetSchema('zinventory')
            rs = dbzinventory.Items_ReportOwner2(ownerID, lastLocationID, lastItemID, rows)
            lines = []
            for r in rs:
                self.BeNice()
                lines.append([self.ItemID(r.itemID),
                 self.ItemTypeAndName(r),
                 self.ItemLocation(r),
                 self.ItemFlag(r),
                 self.ItemAttributes(r),
                 ''])

            customActions = None
            if len(rs) == rows:
                customActions = [self.Button('', 'NEXT %s' % rows, {'action': action,
                  'ownerID': ownerID,
                  'lastLocationID': r.locationID,
                  'lastItemID': r.itemID,
                  'rows': rows}, 'blue')]
            self.WriteTable(['ID',
             'Category, Group, Type, Name',
             'Location',
             'Flag',
             'Attributes',
             'Act'], lines, useFilter=True, customActions=customActions)

        def ItemsLocationTable(self, locationID, lastItemID = None, rows = 200, action = 'ItemsLocation'):
            dbzinventory = self.DB2.GetSchema('zinventory')
            rs = dbzinventory.Items_ReportLocation2(locationID, lastItemID, rows)
            lines = []
            for r in rs:
                self.BeNice()
                lines.append([self.ItemID(r.itemID),
                 self.ItemTypeAndName(r),
                 self.ItemOwner(r),
                 self.ItemFlag(r),
                 self.ItemAttributes(r),
                 ''])

            customActions = None
            if len(lines) == rows:
                customActions = [self.Button('', 'NEXT %s' % rows, {'action': action,
                  'locationID': locationID,
                  'lastItemID': r.itemID,
                  'rows': rows})]
            self.WriteTable(['ID',
             'Category, Group, Type, Name',
             'Owner',
             'Flag',
             'Attributes',
             'Act'], lines, useFilter=True, customActions=customActions)

        def ItemsOwnerLocationTable(self, ownerID, locationID, lastItemID = None, rows = 200, action = 'ItemsOwnerLocation'):
            dbzinventory = self.DB2.GetSchema('zinventory')
            rs = dbzinventory.Items_ReportOwnerLocation2(ownerID, locationID, lastItemID, rows)
            lines = []
            for r in rs:
                self.BeNice()
                lines.append([self.ItemID(r.itemID),
                 self.ItemTypeAndName(r),
                 self.ItemFlag(r),
                 self.ItemAttributes(r),
                 ''])

            customActions = None
            if len(lines) == rows:
                customActions = [self.Button('', 'NEXT %s' % rows, {'action': action,
                  'ownerID': ownerID,
                  'locationID': locationID,
                  'lastItemID': r.itemID,
                  'rows': rows})]
            self.WriteTable(['ID',
             'Category, Group, Type, Name',
             'Flag',
             'Attributes',
             'Act'], lines, useFilter=True, customActions=customActions)

        def WriteInfoReport(self, reportID):
            r = self.DB2.SQLInt('*', 'zreport.reportsEx', '', '', 'reportID', reportID)[0]
            self.WriteH2('Reports: %s - %s' % (self.Link('/info/reports.py', r.groupName, {'action': 'Reports',
              'groupID': r.groupID}), self.FontRed(r.reportName)))
            if r.description != '':
                self.Write(r.description)
                self.WriteBreak(2)
            if r.disabled == 1:
                self.WriteError('Report is disabled')
                return
            if r.disabled == 2 and prefs.clusterMode == 'LIVE':
                self.WriteError('Report is disabled on servers running LIVE')
                return
            ds = self.DB2.GetSchema('zreport').Reports_Execute(session.userid, reportID)
            if type(ds) == types.ListType:
                for rs in ds:
                    self.WriteRowset(rs)
                    self.WriteBreak()

            else:
                self.WriteRowset(ds)

        def WriteLookupTable(self, lookupTableID):
            rs = self.DB2.SQLInt('lookupID, lookupText, description', 'zsystem.lookupValues', '', 'lookupID', 'lookupTableID', lookupTableID)
            self.WriteRowset(rs)

        def GetIngredientName(self, ingredientID):
            import entityCommon
            rs = self.DB2.SQL('SELECT componentID FROM zentity.ingredients WHERE ingredientID = %d' % ingredientID)
            if len(rs) < 1:
                return 'UNKNOWN INGREDIENT'
            else:
                return entityCommon.GetComponentName(rs[0].componentID)

        def GetIngredientLink(self, ingredientID):
            import entityCommon
            rs = self.DB2.SQL('SELECT componentID FROM zentity.ingredients WHERE ingredientID = %d' % ingredientID)
            if len(rs) < 1:
                componentName = 'UNKNOWN INGREDIENT'
            else:
                componentName = entityCommon.GetComponentName(rs[0].componentID)
            return self.Link('entities.py', componentName, {'action': 'Ingredient',
             'ingredientID': ingredientID})

        def GetParentText(self, parentID, parentType):
            if parentType == const.cef.PARENT_SPAWNID:
                return 'Unnamed Spawn'
            elif parentType == const.cef.PARENT_TYPEID:
                return self.SP.TypeName(parentID)
            elif parentType == const.cef.PARENT_GROUPID:
                return self.SP.GroupName(parentID)
            elif parentType == const.cef.PARENT_CATEGORYID:
                return self.SP.CategoryName(parentID)
            else:
                return 'Unknown Parent Type!'

        def GetParentLink(self, parentID, parentType):
            parentName = self.GetParentText(parentID, parentType)
            return self.Link('entities.py', parentName, {'action': 'Recipe',
             'parentID': parentID,
             'parentType': parentType})

        def GetComponentLink(self, componentID):
            import entityCommon
            linkName = entityCommon.GetComponentName(componentID)
            return self.Link('entities.py', linkName, {'action': 'RecipesByComponent',
             'componentID': componentID})
