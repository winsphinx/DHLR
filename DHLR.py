#!/usr/bin/env python2
# -- coding: utf-8 --

import os
import re
import sys
import json
import telnetlib
from PyQt4 import QtCore, QtGui, uic

uifile = os.path.join('.', 'DHLR.ui')
jsfile = os.path.join('.', 'DHLR.cfg')
locale = os.path.join('.', 'DHLR.json')
with open(jsfile, 'r') as f:
    info = json.load(f)
host = str(info['host'])
port = int(info['port'])
username = str(info['username'])
password = str(info['password'])

uiform = uic.loadUiType(uifile)[0]


def convertMessage(data):
    msg = ''
    with open(locale, 'r') as f:
        dict = json.load(f)
    for k in dict['Order']:
        if k in data:
            if data[k] == '':
                data[k] = 'N'
            if k in dict['Locale']:
                name = dict['Locale'][k]
            else:
                name = k
            msg += '<b>' + name + ':  </b>' + data[k] + '<br>'
    return msg


def matchData(data, pattern):
    r = re.compile(pattern, re.S)
    try:
        return r.match(data).groupdict()
    except:
        raise


class DHLRForm(QtGui.QMainWindow, uiform):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.btnQuery.clicked.connect(self.queryUser)
        self.btnLocUpd.clicked.connect(self.updateLocation)
        self.connect(
            self.inputBox,
            QtCore.SIGNAL('returnPressed()'),
            self.queryUser)

    def checkInput(self):
        num = str(self.inputBox.text()).strip()
        if num.isdigit() and num.startswith('861') and len(num) == 13:
            return ('M', num)
        elif num.isdigit() and num.startswith('46001') and len(num) == 15:
            return ('I', num)
        elif num == '':
            self.textBrowser.append(u'<font color=red>请输号码!</font>')
            return
        else:
            self.textBrowser.append(u'<font color=red>格式无效!</font>')
            return

    def getIMSI(self, flag, num):
        if flag == 'M':
            cmd = 'ZMIO:MSISDN=' + num + ';\r'
        elif flag == 'I':
            cmd = 'ZMIO:IMSI=' + num + ';\r'
        else:
            return

        s = DHLR.sendDHLRCmd(cmd)
        if not re.search('FAILED', s):
            r = re.compile('(\d{15})', re.S)
            try:
                return r.search(s).group()
            except:
                raise

    def getCID(self, imsi, vlr):
        if vlr == '8615644011':
            host = '192.91.141.158'
        elif vlr == '8615644650':
            host = '192.91.141.169'
        else:
            return
        server = telnetlib.Telnet(host)
        server.read_until('ENTER USERNAME < ')
        server.write('SXWGZB\r')
        server.read_until('ENTER PASSWORD < ')
        server.write('1Q2W3E4R\r')
        server.read_until('< ', 10)
        server.write('MVO:IMSI=' + imsi + ';\r')
        s = server.read_until('< ', 10)
        if not re.search('FAILED', s):
            r = re.compile(('.*LOCATION AREA CODE OF IMSI \.+ (?P<LAC>[\w\/]*)'
                            '.*RADIO ACCESS INFO \.+ (?P<NET>\w*)'
                            '.*LAST USED CELL ID \.+ (?P<CID>[\w\/]*)'),
                           re.S
                           )
            lac, net, cid = r.match(s).groups()
            if lac != 'N':
                lac = lac.split('/')[1][:-1]
            if cid != 'N':
                cid = cid.split('/')[1][:-1]
            return (net, lac, cid)
        else:
            raise

    def queryUser(self):
        self.textBrowser.clear()
        try:
            DHLR.loginDHLR(host, port, username, password)
        except:
            self.textBrowser.append(u'<font color=red>连接出错!</font>')
            return

        if self.checkInput():
            flag, num = self.checkInput()
            if flag == 'M':
                cmd = 'ZMIO:MSISDN=' + num + ';\r'
            elif flag == 'I':
                cmd = 'ZMIO:IMSI=' + num + ';\r'
        else:
            return

        # To get ZMIO
        s = DHLR.sendDHLRCmd(cmd)
        r = ('.*INTERNATIONAL MOBILE SUBSCRIBER IDENTITY \.+ (?P<IMSI>\d{15})'
             '.*MOBILE STATION ISDN NUMBER \.+ (?P<MSISDN>\d{13})'
             '.*SERVICE AREA OF MSISDN \.+ (?P<SAM>\w{3})'
             '.*VLR-ADDRESS \.+ (?P<VLR>\d*)'
             '.*ROAMING PROFILE INDEX \.+ (?P<RP>\d*)'
             '.*ROAMING TO UTRAN RESTRICTED \.+ (?P<URE>[YN])'
             '.*ROAMING TO GERAN RESTRICTED \.+ (?P<GRE>[YN])'
             '.*LATEST LOCATION UPDATE\s+(?P<VLRT>[T0-9\:\+\-\.]*)'
             )
        try:
            db = matchData(s, r)
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>无效用户!</font>')
            DHLR.closeDHLR()
            return

        # To get ZMSO
        s = DHLR.sendDHLRCmd('ZMSO:IMSI=' + db['IMSI'] + ':BSERV=T11;\r')
        r = ('.*CALL HOLD \.+ (?P<HOLD>[YN])'
             '.*CALLING LINE ID PRESENTATION \.+ (?P<CLIP>[YNO])'
             '.*CALLING LINE ID RESTRICTION \.+ (?P<CLIR>\w*)'
             '.*MULTI PARTY SERVICE \.* (?P<MTPY>[YN])'
             '.*SELECTIVE RINGBACK TONE \.* (?P<SRBT>[YN])'
             '.*BARRING OF ALL MTC \.*  (?P<BAIC>[YNAD ])'
             '.*BARRING OF ALL MOC \.*  (?P<BAOC>[YNAD ])'
             '.*BARRING OF INTERNATIONAL MOC \.*  (?P<BOIC>[YNAD ])'
             '.*CALL FWD UNCONDITIONAL *\.+ (?P<CFU>[\w ]*)'
             '.*CALL FWD ON SUBSCRIBER BUSY *\.+ (?P<CFB>[\w ]*)'
             '.*CALL FWD ON SUBS. NOT REACHABLE  (?P<CFNR>[\w ]*)'
             '.*CALL FWD ON NO REPLY \.+ (?P<CFNA>[\w ]*)'
             '.*OPERATOR CONTROLLED CALL FWD \.+ (?P<OCCF>[\w ]*)'
             '.*CALL WAITING \.* (?P<CW>[YNAD ])'
             )
        try:
            db.update(matchData(s, r))
        except:
            pass

        # To get ZMQO
        s = DHLR.sendDHLRCmd('ZMQO:IMSI=' + db['IMSI'] + ':DISP=CA;\r')
        r = ('.*SERVICE CONTROL POINT ADDRESS\.+(?P<SCP>\d{10})')
        try:
            db.update(matchData(s, r))
        except:
            db['SCP'] = 'N'

        # To Get ZMBO
        s = DHLR.sendDHLRCmd('ZMBO:IMSI=' + db['IMSI'] + ';\r')
        r = re.compile(('([\w]{3}),000'), re.S | re.M)
        try:
            db['SERV'] = ','.join(r.findall(s))
        except:
            pass

        # To get ZMNO
        s = DHLR.sendDHLRCmd('ZMNO:IMSI=' + db['IMSI'] + ';\r')
        r = ('.*SGSN ADDRESS \.+ (?P<SGSN>\d*)'
             '.*NETWORK ACCESS \.+ (?P<NWACC>\w*)'
             )
        try:
            db.update(matchData(s, r))
        except:
            pass
        r = re.compile(('.*?QUALITY OF SERVICES PROFILE . (\d+)'
                        '.*?APN \.+ ([\w\.]*)'),
                       re.S | re.M
                       )
        try:
            db['QOS'] = ','.join(['@'.join(i) for i in r.findall(s)])
        except:
            db['QOS'] = 'N'

        # To Get ZMNF
        s = DHLR.sendDHLRCmd('ZMNF:IMSI=' + db['IMSI'] + ';\r')
        r = ('.*EPS STATUS \.+ (?P<EPS>\w*)'
             '.*MME ADDRESS PRESENT\.+ (?P<MME>[YN])'
             '.*AMBR DOWNLINK \.+ (?P<DN>\d*)'
             '.*AMBR UPLINK \.+ (?P<UP>\d*)'
             '.*LATEST LTE LOCATION UPDATE .. (?P<LTET>[T0-9\:\+\-\.]*)'
             )
        try:
            db.update(matchData(s, r))
            db['LTE'] = "UP:" + db['UP'] + ",DN:" + db['DN']
            db.pop('DN')
            db.pop('UP')
        except:
            pass

        # To Get ZMGO
        s = DHLR.sendDHLRCmd('ZMGO:IMSI=' + db['IMSI'] + ';\r')
        r = ('.*BAOC ... BARRING OF ALL OUTGOING CALLS \.+ (?P<BAOCODB>[YN])'
             '.*BAIC ... BARRING OF ALL INCOMING CALLS \.+ (?P<BAICODB>[YN])'
             )
        try:
            db.update(matchData(s, r))
        except:
            pass

        # To Get LAC/CID
        vlr = db['VLR']
        if vlr == '8615644011' or vlr == '8615644650':
            imsi = db['IMSI']
            try:
                db['NET'], db['LAC'], db['CID'] = self.getCID(imsi, vlr)
            except:
                pass

        self.textBrowser.append(convertMessage(db))
        DHLR.closeDHLR()

    def updateLocation(self):
        self.textBrowser.clear()
        try:
            DHLR.loginDHLR(host, port, username, password)
        except:
            self.textBrowser.append(u'<font color=red>连接出错!</font>')
            return

        if self.checkInput():
            flag, num = self.checkInput()
            try:
                imsi = self.getIMSI(flag, num)
                DHLR.sendDHLRCmd('ZMIM:IMSI=' + imsi + ':VLR=N;\r')
                self.textBrowser.append(u'<font color=green>操作成功!</font>')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!</font>')

        DHLR.closeDHLR()


class DHLRTelnet(object):

    def __init__(self, telnet=telnetlib.Telnet()):
        self.telnet = telnet

    def loginDHLR(self, host, port, username, password):
        try:
            self.telnet.open(host, port)
            self.telnet.read_until('ENTER USERNAME < ')
            self.telnet.write(username + '\r')
            self.telnet.read_until('ENTER PASSWORD < ')
            self.telnet.write(password + '\r')
            self.telnet.read_until('< ', 10)
        except:
            raise

    def closeDHLR(self):
        self.telnet.close()

    def sendDHLRCmd(self, cmd):
        self.telnet.write(cmd)
        return self.telnet.read_until('< ', 10)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    DHLR = DHLRTelnet()
    DHLRWin = DHLRForm()
    DHLRWin.show()
    app.exec_()
