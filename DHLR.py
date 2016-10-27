#!/usr/bin/env python2
# -- coding: utf-8 --

import os
import re
import sys
import json
import telnetlib
from PyQt4 import QtCore, QtGui, uic
from CFX import CFxFrame

uifile = os.path.join('.', 'DHLR.ui')
config = os.path.join('.', 'DHLR.json')
with open(config, 'r') as f:
    cfg = json.load(f)
host = str(cfg['HLR']['host'])
port = int(cfg['HLR']['port'])
username = str(cfg['HLR']['username'])
password = str(cfg['HLR']['password'])

uiform = uic.loadUiType(uifile)[0]


def convert_msg(data):
    msg = ''
    for k in cfg['Order']:
        if k in data:
            if data[k] == '':
                data[k] = 'N'
            if k in cfg['Locale']:
                name = cfg['Locale'][k]
            else:
                name = k
            msg += '<b>' + name + ':  </b>' + data[k] + '<br>'
    return msg


def match_data(data, pattern):
    r = re.compile(pattern, re.S)
    try:
        return r.match(data).groupdict()
    except:
        raise


class DHLRForm(QtGui.QMainWindow, uiform):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.btnQuery.clicked.connect(self.query_user)
        self.btnLocUpd.clicked.connect(self.update_location)
        self.btn4to3.clicked.connect(self.four_three)
        self.btn3to2.clicked.connect(self.three_two)
        self.btn2to3.clicked.connect(self.two_three)
        self.btn3to4.clicked.connect(self.three_four)
        self.btnQueryOther.clicked.connect(self.query_other)
        self.btnCFx.clicked.connect(self.call_forward)
        self.connect(
            self.inputBox,
            QtCore.SIGNAL('returnPressed()'),
            self.query_user)

    def check_input(self):
        num = str(self.inputBox.text()).strip()
        if num.isdigit() and num.startswith('861') and len(num) == 13:
            return ('M', num)
        elif num.isdigit() and num.startswith('46001') and len(num) == 15:
            return ('I', num)
        elif num == '':
            self.textBrowser.append(u'<font color=red>请输号码!')
            return
        else:
            self.textBrowser.append(u'<font color=red>格式无效!')
            return

    def get_imsi(self, flag, num):
        if flag == 'M':
            cmd = 'ZMIO:MSISDN=' + num + ';\r'
        elif flag == 'I':
            cmd = 'ZMIO:IMSI=' + num + ';\r'
        else:
            return

        s = DHLR.send_cmd(cmd)
        if not re.search('FAILED', s):
            r = re.compile('(\d{15})', re.S)
            try:
                return r.search(s).group()
            except:
                raise

    def get_cid(self, msisdn, vlr):
        host = cfg['VLR'][vlr]
        server = telnetlib.Telnet(host)
        server.read_until('ENTER USERNAME < ')
        server.write('SXWGZB\r')
        server.read_until('ENTER PASSWORD < ')
        server.write('1Q2W3E4R\r')
        server.read_until('< ', 10)
        server.write('MVO:MSISDN=' + msisdn + ';\r')
        s = server.read_until('< ', 10)
        server.close()
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

    def query_user(self):
        self.textBrowser.clear()
        try:
            DHLR.login_dev(host, port, username, password)
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if flag == 'M':
                cmd = 'ZMIO:MSISDN=' + num + ';\r'
            elif flag == 'I':
                cmd = 'ZMIO:IMSI=' + num + ';\r'
        else:
            return

        # To get ZMIO
        s = DHLR.send_cmd(cmd)
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
            db = match_data(s, r)
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>无效用户!')
            DHLR.close_dev()
            return

        # To get ZMSO
        s = DHLR.send_cmd('ZMSO:IMSI=' + db['IMSI'] + ':BSERV=T11;\r')
        r = ('.*CALL HOLD \.+ (?P<HOLD>[YN])'
             '.*CALLING LINE ID PRESENTATION \.+ (?P<CLIP>[YNO])'
             '.*CALLING LINE ID RESTRICTION \.+ (?P<CLIR>\w*)'
             '.*MULTI PARTY SERVICE \.* (?P<MTPY>[YN])'
             '.*SELECTIVE RINGBACK TONE \.* (?P<SRBT>[YN])'
             '.*BARRING OF ALL MTC \.*  (?P<BAIC>[YNAD ]*)'
             '.*BARRING OF ALL MOC \.*  (?P<BAOC>[YNAD ]*)'
             '.*BARRING OF INTERNATIONAL MOC \.*  (?P<BOIC>[YNAD ]*)'
             '.*CALL FWD UNCONDITIONAL *\.+ (?P<CFU>[\w ]*)'
             '.*CALL FWD ON SUBSCRIBER BUSY *\.+ (?P<CFB>[\w ]*)'
             '.*CALL FWD ON SUBS. NOT REACHABLE  (?P<CFNR>[\w ]*)'
             '.*CALL FWD ON NO REPLY \.+ (?P<CFNA>[\w ]*)'
             '.*OPERATOR CONTROLLED CALL FWD \.+ (?P<OCCF>[\w ]*)'
             '.*CALL WAITING \.* (?P<CW>[YNAD ]*)'
             )
        try:
            db.update(match_data(s, r))
        except:
            pass

        # To get ZMQO
        s = DHLR.send_cmd('ZMQO:IMSI=' + db['IMSI'] + ':DISP=CA;\r')
        r = ('.*SERVICE CONTROL POINT ADDRESS\.+(?P<SCP>\d{10})')
        try:
            db.update(match_data(s, r))
        except:
            db['SCP'] = 'N'

        # To Get ZMBO
        s = DHLR.send_cmd('ZMBO:IMSI=' + db['IMSI'] + ';\r')
        r = re.compile(('([\w]{3}),000'), re.S | re.M)
        try:
            db['SERV'] = ','.join(r.findall(s))
        except:
            pass

        # To get ZMNO
        s = DHLR.send_cmd('ZMNO:IMSI=' + db['IMSI'] + ';\r')
        r = ('.*SGSN ADDRESS \.+ (?P<SGSN>\d*)'
             '.*NETWORK ACCESS \.+ (?P<NWACC>\w*)'
             )
        try:
            db.update(match_data(s, r))
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
        s = DHLR.send_cmd('ZMNF:IMSI=' + db['IMSI'] + ';\r')
        r = ('.*EPS STATUS \.+ (?P<EPS>\w*)'
             '.*MME ADDRESS PRESENT\.+ (?P<MME>[YN])'
             '.*AMBR DOWNLINK \.+ (?P<DN>\d*)'
             '.*AMBR UPLINK \.+ (?P<UP>\d*)'
             '.*LATEST LTE LOCATION UPDATE .. (?P<LTET>[T0-9\:\+\-\.]*)'
             )
        try:
            db.update(match_data(s, r))
            db['LTE'] = 'UP:' + db['UP'] + ',DN:' + db['DN']
            db.pop('DN')
            db.pop('UP')
        except:
            pass

        # To Get ZMGO
        s = DHLR.send_cmd('ZMGO:IMSI=' + db['IMSI'] + ';\r')
        r = ('.*BAOC ... BARRING OF ALL OUTGOING CALLS \.+ (?P<BAOCODB>[YN])'
             '.*BAIC ... BARRING OF ALL INCOMING CALLS \.+ (?P<BAICODB>[YN])'
             )
        try:
            db.update(match_data(s, r))
        except:
            pass

        # To Get LAC/CID
        vlr = db['VLR']
        if vlr in cfg['VLR'].keys():
            msisdn = db['MSISDN']
            try:
                db['NET'], db['LAC'], db['CID'] = self.get_cid(msisdn, vlr)
            except:
                pass

        self.textBrowser.append(convert_msg(db))
        DHLR.close_dev()

    def update_location(self):
        self.textBrowser.clear()
        try:
            DHLR.login_dev(host, port, username, password)
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                DHLR.send_cmd('ZMIM:IMSI=' + imsi + ':VLR=N;\r')
                self.textBrowser.append(u'<font color=green>操作成功!')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')

        DHLR.close_dev()

    def four_three(self):
        self.textBrowser.clear()
        try:
            DHLR.login_dev(host, port, username, password)
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return
        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                DHLR.send_cmd('ZMNE:IMSI=' + imsi + ':STATUS=DENIED;\r')
                self.textBrowser.append(u'<font color=green>操作成功!')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')

    def three_four(self):
        self.textBrowser.clear()
        try:
            DHLR.login_dev(host, port, username, password)
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return
        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                DHLR.send_cmd('ZMNE:IMSI=' + imsi + ':STATUS=GRANTED;\r')
                self.textBrowser.append(u'<font color=green>操作成功!')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')

    def three_two(self):
        self.textBrowser.clear()
        try:
            DHLR.login_dev(host, port, username, password)
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return
        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                DHLR.send_cmd('ZMIM:IMSI=' + imsi + ':UREST=Y;\r')
                self.textBrowser.append(u'<font color=green>操作成功!')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')

    def two_three(self):
        self.textBrowser.clear()
        try:
            DHLR.login_dev(host, port, username, password)
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return
        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                DHLR.send_cmd('ZMIM:IMSI=' + imsi + ':UREST=N;\r')
                self.textBrowser.append(u'<font color=green>操作成功!')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')

    def query_other(self):
        self.textBrowser.clear()
        if self.check_input():
            _, msisdn = self.check_input()
            db = {}
            found = 0
        for vlr in cfg['VLR'].keys():
            try:
                db['NET'], db['LAC'], db['CID'] = self.get_cid(msisdn, vlr)
                db['VLR'] = vlr
                found = 1
                self.textBrowser.append(convert_msg(db))
            except:
                pass
        if not found:
            self.textBrowser.append(u'<font color=red>没有登网/外地!')

    def call_forward(self):
        f = CFxFrame()
        fn = f.cfx_num
        ft = f.cfx_type
        self.textBrowser.clear()
        if ft and fn:
            try:
                DHLR.login_dev(host, port, username, password)
            except:
                self.textBrowser.append(u'<font color=red>连接出错!')
                return
            if self.check_input():
                flag, num = self.check_input()
                try:
                    imsi = self.get_imsi(flag, num)
                    cmd = 'ZMSS:IMSI=' + imsi + ':' + ft + '=' + fn + ';\r'
                    DHLR.send_cmd(cmd)
                    self.textBrowser.append(u'<font color=green>操作成功!')
                except:
                    self.textBrowser.append(u'<font color=red>无效用户!')
        else:
            self.textBrowser.append(u'<font color=red>无效操作!')


class DHLRTelnet(object):

    def __init__(self, telnet=telnetlib.Telnet()):
        self.telnet = telnet

    def login_dev(self, host, port, username, password):
        try:
            self.telnet.open(host, port)
            self.telnet.read_until('ENTER USERNAME < ')
            self.telnet.write(username + '\r')
            self.telnet.read_until('ENTER PASSWORD < ')
            self.telnet.write(password + '\r')
            self.telnet.read_until('< ', 10)
        except:
            raise

    def close_dev(self):
        self.telnet.close()

    def send_cmd(self, cmd):
        self.telnet.write(cmd)
        return self.telnet.read_until('< ', 10)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    DHLR = DHLRTelnet()
    DHLRWin = DHLRForm()
    DHLRWin.show()
    app.exec_()
