#!/usr/bin/env python2
# -- coding: utf-8 --

import os
import re
import sys
import json
import telnetlib
from PyQt4 import QtCore, QtGui, uic
from CFX import CFxFrame

path = os.path.dirname(sys.argv[0])
uifile = os.path.join(path, 'DHLR.ui')
uiform = uic.loadUiType(uifile)[0]
cfgfile = os.path.join(path, 'DHLR.json')
with open(cfgfile, 'r') as f:
    cfg = json.load(f)


class DHLRForm(QtGui.QMainWindow, uiform):

    def __init__(self, parent=None, telnet=telnetlib.Telnet()):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.telnet = telnet
        self.btnQuery.clicked.connect(self.query_user)
        self.btnLocUpd.clicked.connect(self.update_location)
        self.btn4to3.clicked.connect(self.four_three)
        self.btn3to2.clicked.connect(self.three_two)
        self.btn2to3.clicked.connect(self.two_three)
        self.btn3to4.clicked.connect(self.three_four)
        self.btnQueryOther.clicked.connect(self.query_other)
        self.btnCFx.clicked.connect(self.call_forward)
        self.btnStop.clicked.connect(self.stop_num)
        self.btnRest.clicked.connect(self.rest_num)
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

        s = self.send_cmd(cmd)
        if not re.search('FAILED', s):
            r = re.compile('(\d{15})', re.S)
            try:
                return r.search(s).group()
            except:
                pass

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
                            '.*LAST ACTIVATE DATE \.+ (?P<TIME>[\d\:\- ]*)'
                            '.*LAST USED CELL ID \.+ (?P<CID>[\w\/]*)'),
                           re.S
                           )
            lac, net, time, cid = r.match(s).groups()
            if lac != 'N':
                lac = lac.split('/')[1][:-1]
            if cid != 'N':
                cid = cid.split('/')[1][:-1]
            return (net, lac, cid, time)

    def query_user(self):
        self.textBrowser.clear()
        try:
            self.login_dev(cfg['HLR'])
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
        s = self.send_cmd(cmd)
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
            db = self.match_data(s, r)
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>无效用户!')
            self.close_dev()
            return

        # To get ZMSO
        s = self.send_cmd('ZMSO:IMSI=' + db['IMSI'] + ':BSERV=T11;\r')
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
            db.update(self.match_data(s, r))
        except:
            pass

        # To get ZMQO
        s = self.send_cmd('ZMQO:IMSI=' + db['IMSI'] + ':DISP=CA;\r')
        r = ('.*SERVICE CONTROL POINT ADDRESS\.+(?P<SCP>\d{10})')
        try:
            db.update(self.match_data(s, r))
        except:
            db['SCP'] = 'N'

        # To Get ZMBO
        s = self.send_cmd('ZMBO:IMSI=' + db['IMSI'] + ';\r')
        r = re.compile(('([\w]{3}),000'), re.S | re.M)
        try:
            db['SERV'] = ','.join(r.findall(s))
        except:
            pass

        # To get ZMNO
        s = self.send_cmd('ZMNO:IMSI=' + db['IMSI'] + ';\r')
        r = ('.*SGSN ADDRESS \.+ (?P<SGSN>\d*)'
             '.*NETWORK ACCESS \.+ (?P<NWACC>\w*)'
             )
        try:
            db.update(self.match_data(s, r))
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
        s = self.send_cmd('ZMNF:IMSI=' + db['IMSI'] + ';\r')
        r = ('.*EPS STATUS \.+ (?P<EPS>\w*)'
             '.*MME ADDRESS PRESENT\.+ (?P<MME>[YN])'
             '.*AMBR DOWNLINK \.+ (?P<DN>\d*)'
             '.*AMBR UPLINK \.+ (?P<UP>\d*)'
             '.*LATEST LTE LOCATION UPDATE .. (?P<LTET>[T0-9\:\+\-\.]*)'
             )
        try:
            db.update(self.match_data(s, r))
        except:
            pass
        else:
            db['LTE'] = 'DN:' + db['DN'] + ',UP:' + db['UP']
            db.pop('DN')
            db.pop('UP')

        # To Get ZMGO
        s = self.send_cmd('ZMGO:IMSI=' + db['IMSI'] + ';\r')
        r = ('.*BAOC ... BARRING OF ALL OUTGOING CALLS \.+ (?P<BAOCODB>[YN])'
             '.*BAIC ... BARRING OF ALL INCOMING CALLS \.+ (?P<BAICODB>[YN])'
             )
        try:
            db.update(self.match_data(s, r))
        except:
            pass

        # To Get LAC/CID
        vlr = db['VLR']
        if vlr in cfg['VLR'].keys():
            msisdn = db['MSISDN']
            try:
                db['NET'], db['LAC'], db['CID'], _ = self.get_cid(msisdn, vlr)
            except:
                pass

        self.textBrowser.append(self.convert_msg(db))
        self.close_dev()

    def update_location(self):
        self.textBrowser.clear()
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                self.send_cmd('ZMIM:IMSI=' + imsi + ':VLR=N;\r')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')
            else:
                self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def four_three(self):
        self.textBrowser.clear()
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return
        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                self.send_cmd('ZMNE:IMSI=' + imsi + ':STATUS=DENIED;\r')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')
            else:
                self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def three_four(self):
        self.textBrowser.clear()
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return
        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                self.send_cmd('ZMNE:IMSI=' + imsi + ':STATUS=GRANTED;\r')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')
            else:
                self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def three_two(self):
        self.textBrowser.clear()
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return
        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                self.send_cmd('ZMIM:IMSI=' + imsi + ':UREST=Y;\r')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')
            else:
                self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def two_three(self):
        self.textBrowser.clear()
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return
        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                self.send_cmd('ZMIM:IMSI=' + imsi + ':UREST=N;\r')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')
            else:
                self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def query_other(self):
        self.textBrowser.clear()
        if self.check_input():
            _, msisdn = self.check_input()
            db = {}
            found = 0
        for vlr in cfg['VLR'].keys():
            try:
                db['VLR'] = vlr
                db['NET'], db['LAC'], db['CID'], db['TIME'] = \
                    self.get_cid(msisdn, vlr)
            except:
                pass
            else:
                found = 1
                self.textBrowser.append(self.convert_msg(db))
        if not found:
            self.textBrowser.append(u'<font color=red>没有登网/外地!')

    def call_forward(self):
        f = CFxFrame()
        fn = f.cfx_num
        ft = f.cfx_type
        self.textBrowser.clear()
        if ft and fn:
            try:
                self.login_dev(cfg['HLR'])
            except:
                self.textBrowser.append(u'<font color=red>连接出错!')
                return
            if self.check_input():
                flag, num = self.check_input()
                try:
                    imsi = self.get_imsi(flag, num)
                    cmd = 'ZMSS:IMSI=' + imsi + ':' + ft + '=' + fn + ';\r'
                    self.send_cmd(cmd)
                except:
                    self.textBrowser.append(u'<font color=red>无效用户!')
                else:
                    self.textBrowser.append(u'<font color=green>操作成功!')
        else:
            self.textBrowser.append(u'<font color=red>无效操作!')

        self.close_dev()

    def stop_num(self):
        self.textBrowser.clear()
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                self.send_cmd('ZMGC:IMSI=' + imsi + ':CBO=BAOC,CBI=BAIC;\r')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')
            else:
                self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def rest_num(self):
        self.textBrowser.clear()
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
                self.send_cmd('ZMGD:IMSI=' + imsi + ';\r')
            except:
                self.textBrowser.append(u'<font color=red>无效用户!')
            else:
                self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def login_dev(self, device):
        host = str(device['host'])
        port = int(device['port'])
        username = str(device['username'])
        password = str(device['password'])
        try:
            self.telnet.open(host, port)
            self.telnet.read_until('ENTER USERNAME < ')
            self.telnet.write(username + '\r')
            self.telnet.read_until('ENTER PASSWORD < ')
            self.telnet.write(password + '\r')
            self.telnet.read_until('< ', 10)
        except:
            pass

    def close_dev(self):
        self.telnet.close()

    def send_cmd(self, cmd):
        self.telnet.write(cmd)
        return self.telnet.read_until('< ', 10)

    def convert_msg(self, data):
        msg = ''
        for k in cfg['Order']:
            if k in data:
                if data[k] == '':
                    data[k] = 'N'
                name = cfg['Locale'].get(k, k)
                msg += '<b>' + name + ':  </b>' + data[k] + '<br>'
        return msg

    def match_data(self, data, pattern):
        r = re.compile(pattern, re.S)
        try:
            return r.match(data).groupdict()
        except:
            pass


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    DHLRWin = DHLRForm()
    DHLRWin.show()
    app.exec_()
