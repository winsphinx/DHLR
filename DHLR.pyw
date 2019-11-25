#!/usr/bin/env python2
# -- coding: utf-8 --

import json
import os
import re
import sys
import telnetlib
import Tkinter as T

import tkMessageBox
from PyQt4 import QtCore, QtGui, uic

path = os.path.dirname(sys.argv[0])
uifile = os.path.join(path, 'DHLR.ui')
logfile = os.path.join(path, 'DHLR.log')
cfgfile = os.path.join(path, 'DHLR.json')
uiform = uic.loadUiType(uifile)[0]
with open(cfgfile, 'r') as f:
    cfg = json.load(f)


class DHLRForm(QtGui.QMainWindow, uiform):
    def __init__(self, parent=None, telnet=telnetlib.Telnet()):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.statusBar().showMessage(' Ready')
        self.telnet = telnet
        self.btnQuery.clicked.connect(self.query_user)
        self.btnLocUpd.clicked.connect(self.update_location)
        self.btn2off.clicked.connect(self.two_off)
        self.btn2on.clicked.connect(self.two_on)
        self.btn3off.clicked.connect(self.three_off)
        self.btn3on.clicked.connect(self.three_on)
        self.btn4off.clicked.connect(self.four_off)
        self.btn4on.clicked.connect(self.four_on)
        self.btnQueryOther.clicked.connect(self.query_other)
        self.btnCFx.clicked.connect(self.call_forward)
        self.btnStop.clicked.connect(self.stop_num)
        self.btnRest.clicked.connect(self.rest_num)
        self.btnKickOut.clicked.connect(self.kick)
        self.connect(self.inputBox, QtCore.SIGNAL('returnPressed()'),
                     self.query_user)
        self.menu_openLog.triggered.connect(lambda: self.open_log(logfile))
        self.menu_clearLog.triggered.connect(lambda: self.init_log(logfile))

    def check_input(self):
        num = str(self.inputBox.text()).strip()
        if num.isdigit() and num.startswith('861') and len(num) == 13:
            return ('M', num)
        elif num.isdigit() and num.startswith('4600') and len(num) == 15:
            return ('I', num)
        elif num == '':
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>请输号码!')
            return
        else:
            self.textBrowser.clear()
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
                raise

    def get_vlr_info(self, msisdn, vlr):
        self.statusBar().showMessage(' Connected!')
        host = cfg['VLR'][vlr]
        server = telnetlib.Telnet(host)
        server.read_until('ENTER USERNAME < ')
        server.write(str(cfg['Login']['username']) + '\r')
        server.read_until('ENTER PASSWORD < ')
        server.write(str(cfg['Login']['password']) + '\r')
        server.read_until('< ', 10)
        server.write('ZMVO:MSISDN=' + msisdn + ';\r')
        s = server.read_until('< ', 10)
        server.write('ZMWI:MSISDN=' + msisdn + ';\r')
        s += server.read_until('< ', 10)
        server.close()
        self.statusBar().showMessage(' Disconnected')
        if not re.search('FAILED', s):
            r = re.compile((
                '.*INTERNATIONAL MOBILE SUBSCRIBER IDENTITY \.+ (?P<IMSI>\d{15})'
                '.*LOCATION AREA CODE OF IMSI \.+ (?P<LAC>[\w\/]*)'
                '.*RADIO ACCESS INFO \.+ (?P<NET>\w*)'
                '.*IMSI DETACH FLAG \.+ (?P<DEA>[YN])'
                '.*LAST ACTIVATE DATE \.+ (?P<TIME>[\d\:\- ]*)'
                '.*LAST USED CELL ID \.+ (?P<CID>[\w\/]*)'
                '.*INTERNATIONAL MOBILE STATION EQUIPMENT IDENTITY \.+ (?P<IMEI>\d{14})'
            ), re.S)
            imsi, lac, net, dea, time, cid, imei = r.match(s).groups()
            if lac != 'N':
                lac = lac.split('/')[1][:-1]
            if cid != 'N':
                cid = cid.split('/')[1][:-1]
            return (imsi, net, lac, cid, dea, time, imei)

    def query_user(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if flag == 'M':
                cmd = 'ZMIO:MSISDN=' + num + ';\r'
            elif flag == 'I':
                cmd = 'ZMIO:IMSI=' + num + ';\r'
        else:
            self.close_dev()
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
             '.*LATEST LOCATION UPDATE\s+(?P<VLRT>[T0-9\:\+\-\.]*)')
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
             '.*CALL WAITING \.* (?P<CW>[YNAD ]*)')
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
             '.*NETWORK ACCESS \.+ (?P<NWACC>\w*)')
        try:
            db.update(self.match_data(s, r))
        except:
            pass
        r = re.compile(('.*?QUALITY OF SERVICES PROFILE . (\d+)'
                        '.*?APN \.+ ([\w\.]*)'), re.S | re.M)
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
             '.*LATEST LTE LOCATION UPDATE .. (?P<LTET>[T0-9\:\+\-\.]*)')
        try:
            db.update(self.match_data(s, r))
        except:
            pass
        else:
            db['LTE'] = 'DN:' + db['DN'] + ',UP:' + db['UP']
            db.pop('DN')
            db.pop('UP')

        # To Get ZMNI
        s = self.send_cmd('ZMNI:IMSI=' + db['IMSI'] + ';\r')
        r = re.compile(('.*?AP NAME \.+ ([\w\.]*)'), re.S | re.M)
        try:
            db['AP4'] = ','.join([i for i in r.findall(s)])
        except:
            db['AP4'] = 'N'

        # To Get ZMGO
        s = self.send_cmd('ZMGO:IMSI=' + db['IMSI'] + ';\r')
        r = ('.*BAOC ... BARRING OF ALL OUTGOING CALLS \.+ (?P<BAOCODB>[YN])'
             '.*BAIC ... BARRING OF ALL INCOMING CALLS \.+ (?P<BAICODB>[YN])')
        try:
            db.update(self.match_data(s, r))
        except:
            pass

        # To Get LAC/CID
        vlr = db['VLR']
        if vlr in cfg['VLR'].keys():
            msisdn = db['MSISDN']
            try:
                _, db['NET'], db['LAC'], db['CID'], db['DEA'], db['TIME'], db[
                    'IMEI'] = self.get_vlr_info(msisdn, vlr)
            except:
                pass

        self.textBrowser.clear()
        self.textBrowser.append(self.convert_msg(db))
        self.close_dev()

    def update_location(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if Confirm('确认对 ' + num + ' 做位置更新?').comfirmed:
                try:
                    imsi = self.get_imsi(flag, num)
                    self.send_cmd('ZMIM:IMSI=' + imsi + ':VLR=N;\r')
                except:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=red>无效用户!')
                else:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def four_off(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if Confirm('确认对 ' + num + ' 做降网?').comfirmed:
                try:
                    imsi = self.get_imsi(flag, num)
                    self.send_cmd('ZMNE:IMSI=' + imsi + ':STATUS=DENIED;\r')
                except:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=red>无效用户!')
                else:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def four_on(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if Confirm('确认对 ' + num + ' 做升网?').comfirmed:
                try:
                    imsi = self.get_imsi(flag, num)
                    self.send_cmd('ZMNE:IMSI=' + imsi + ':STATUS=GRANTED;\r')
                except:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=red>无效用户!')
                else:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def three_off(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if Confirm('确认对 ' + num + ' 做降网?').comfirmed:
                try:
                    imsi = self.get_imsi(flag, num)
                    self.send_cmd('ZMIM:IMSI=' + imsi + ':UREST=Y;\r')
                except:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=red>无效用户!')
                else:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def three_on(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if Confirm('确认对 ' + num + ' 做升网?').comfirmed:
                try:
                    imsi = self.get_imsi(flag, num)
                    self.send_cmd('ZMIM:IMSI=' + imsi + ':UREST=N;\r')
                except:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=red>无效用户!')
                else:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def two_off(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if Confirm('确认对 ' + num + ' 做降网?').comfirmed:
                try:
                    imsi = self.get_imsi(flag, num)
                    self.send_cmd('ZMIM:IMSI=' + imsi + ':GREST=Y;\r')
                except:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=red>无效用户!')
                else:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def two_on(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if Confirm('确认对 ' + num + ' 做升网?').comfirmed:
                try:
                    imsi = self.get_imsi(flag, num)
                    self.send_cmd('ZMIM:IMSI=' + imsi + ':GREST=N;\r')
                except:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=red>无效用户!')
                else:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def kick(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if Confirm('确认对 ' + num + ' 做踢线?').comfirmed:
                try:
                    imsi = self.get_imsi(flag, num)
                    self.send_cmd('ZMIM:IMSI=' + imsi + ':UREST=Y;\r')
                    self.send_cmd('ZMIM:IMSI=' + imsi + ':UREST=N;\r')
                    self.send_cmd('ZMIM:IMSI=' + imsi + ':GREST=Y;\r')
                    self.send_cmd('ZMIM:IMSI=' + imsi + ':GREST=N;\r')
                except:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=red>无效用户!')
                else:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def query_other(self):
        db = {}
        if self.check_input():
            _, msisdn = self.check_input()
            found = 0
            for vlr in cfg['VLR'].keys():
                db['VLR'] = vlr
                try:
                    db['IMSI'], db['NET'], db['LAC'], db['CID'], db['DEA'], db[
                        'TIME'], db['IMEI'] = self.get_vlr_info(msisdn, vlr)
                except:
                    pass
                else:
                    found = 1
                    self.textBrowser.clear()
                    self.textBrowser.append(self.convert_msg(db))
            if not found:
                self.textBrowser.clear()
                self.textBrowser.append(u'<font color=red>没有位置信息!')

    def call_forward(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            try:
                imsi = self.get_imsi(flag, num)
            except:
                self.textBrowser.clear()
                self.textBrowser.append(u'<font color=red>无效用户!')
            else:
                f = CFxFrame()
                if f.cfx_type and f.cfx_num:
                    cmd = 'ZMSS:IMSI=' + imsi + ':' + f.cfx_type + '=' + f.cfx_num + ';\r'
                    self.send_cmd(cmd)
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=green>操作成功!')
                else:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=red>无效操作!')

        self.close_dev()

    def stop_num(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if Confirm('确认对 ' + num + ' 做停机?').comfirmed:
                try:
                    imsi = self.get_imsi(flag, num)
                    self.send_cmd('ZMGC:IMSI=' + imsi +
                                  ':CBO=BAOC,CBI=BAIC;\r')
                except:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=red>无效用户!')
                else:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def rest_num(self):
        try:
            self.login_dev(cfg['HLR'])
        except:
            self.textBrowser.clear()
            self.textBrowser.append(u'<font color=red>连接出错!')
            return

        if self.check_input():
            flag, num = self.check_input()
            if Confirm('确认对 ' + num + ' 做复机?').comfirmed:
                try:
                    imsi = self.get_imsi(flag, num)
                    self.send_cmd('ZMGD:IMSI=' + imsi + ';\r')
                except:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=red>无效用户!')
                else:
                    self.textBrowser.clear()
                    self.textBrowser.append(u'<font color=green>操作成功!')

        self.close_dev()

    def login_dev(self, device):
        self.statusBar().showMessage(' Connecting...')
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
            self.statusBar().showMessage(' Connected!')
        except:
            self.statusBar().showMessage(' Connect failed!')
            raise

    def close_dev(self):
        self.telnet.close()
        self.statusBar().showMessage(' Disconnected')

    def send_cmd(self, cmd):
        self.telnet.write(cmd)
        result = self.telnet.read_until('< ', 10)
        self.save_log(result, logfile)
        return result

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
            raise

    def open_log(self, log):
        self.textBrowser.clear()
        try:
            with open(log, 'r') as f:
                txt = f.read()
        except:
            txt = u'<font color=red>没有日志!'
        finally:
            self.textBrowser.setText(txt)

    def save_log(self, cmd, log):
        f = open(log, 'a')
        f.write(cmd.rstrip())
        f.close()

    def init_log(self, log):
        try:
            f = open(log, 'w')
            f.truncate()
            f.close()
        except:
            pass
        self.textBrowser.clear()
        self.textBrowser.append(u'<font color=green>操作成功!')


class CFxFrame(object):
    def __init__(self):
        self.cfx_num = ''
        self.cfx_type = ''
        self.frame = T.Tk()
        self.frame.title('呼转')
        self.var = T.StringVar()
        self.var.set('CFU')
        for o, i in enumerate(['CFU', 'CFB', 'CFNA', 'CFNR', 'OCCF']):
            T.Radiobutton(self.frame, text=i, variable=self.var,
                          value=i).grid(row=0, column=o)
        T.Label(self.frame, text='  - 选择呼转分类，并输入呼转号码。').grid(row=1,
                                                             column=0,
                                                             columnspan=4,
                                                             sticky=T.W)
        T.Label(self.frame,
                text='    格式为: 8613004602000 或 8657512345678').grid(
                    row=2, column=0, columnspan=4, sticky=T.W)
        T.Label(self.frame, text='  - 选择分类，号码留空，则取消对应呼转。').grid(row=3,
                                                                column=0,
                                                                columnspan=4,
                                                                sticky=T.W)
        T.Label(self.frame, text='  呼转号码: ').grid(row=4, column=0, sticky=T.W)
        self.num = T.Entry(self.frame)
        self.num.focus_set()
        self.num.grid(row=4, column=1, columnspan=2, sticky=T.EW)
        T.Button(self.frame, text='OK', command=self.ok_clicked).grid(row=4,
                                                                      column=3)
        self.frame.mainloop()

    def num_validated(self, num):
        return (num.isdigit() and num.startswith('86') or num == 'E')

    def ok_clicked(self):
        n = self.num.get().strip() or 'E'
        v = self.var.get().strip()
        if not self.num_validated(n):
            tkMessageBox.showerror(
                '错误', '呼转号码格式无效!\n例子:\n8613004602000\n86575xxxxxxxx')
        else:
            d = {
                'CFU': '无条件',
                'CFB': '遇忙',
                'CFNA': '无应答',
                'CFNR': '无网络',
                'OCCF': '隐含呼转'
            }
            if n == 'E':
                if tkMessageBox.askokcancel('警告', '确认要取消 *' + d[v] + '* 呼转?'):
                    self.cfx_num = n
                    self.cfx_type = v
                    self.frame.destroy()
            else:
                if tkMessageBox.askokcancel(
                        '警告', '确认要 *' + d[v] + '* 呼转到 ' + n + ' ?'):
                    self.cfx_num = n
                    self.cfx_type = v
                    self.frame.destroy()


class Confirm(object):
    def __init__(self, msg):
        self.msg = msg
        self.box = T.Tk()
        self.box.withdraw()
        if tkMessageBox.askokcancel('警告', msg):
            self.comfirmed = 1
            self.box.destroy()
        else:
            self.comfirmed = 0
            self.box.destroy()


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    DHLRWin = DHLRForm()
    DHLRWin.show()
    app.exec_()
