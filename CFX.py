#!/usr/bin/env python
# -*- coding: utf-8 -*-

import Tkinter as T
import tkMessageBox


class CFxFrame(object):

    def __init__(self):
        self.cfx_num = ''
        self.cfx_type = ''
        self.frame = T.Tk()
        self.frame.title('呼转')
        self.var = T.StringVar()
        self.var.set('CFU')
        for o, i in enumerate(['CFU', 'CFB', 'CFNA', 'CFNR']):
            T.Radiobutton(self.frame, text=i, variable=self.var, value=i).grid(row=0, column=o)
        T.Label(self.frame, text='  - 选择呼转分类，并输入呼转号码。').grid(row=1, column=0, columnspan=4, sticky=T.W)
        T.Label(self.frame, text='    格式为: 8613004602000 或 8657512345678').grid(row=2, column=0, columnspan=4, sticky=T.W)
        T.Label(self.frame, text='  - 选择分类，号码留空，则取消对应呼转。').grid(row=3, column=0, columnspan=4, sticky=T.W)
        T.Label(self.frame, text='  呼转号码: ').grid(row=4, column=0, sticky=T.W)
        self.num = T.Entry(self.frame)
        self.num.focus_set()
        self.num.grid(row=4, column=1, columnspan=2, sticky=T.EW)
        T.Button(self.frame, text='OK', command=self.ok_clicked).grid(row=4, column=3)
        self.frame.mainloop()

    def num_validated(self, num):
        if num.isdigit() and num.startswith('86') or num == 'E':
            return True
        else:
            return False

    def ok_clicked(self):
        # self.num.config(state=T.NORMAL)
        n = self.num.get().strip() or 'E'
        v = self.var.get().strip()
        if not self.num_validated(n):
            tkMessageBox.showerror('错误', '呼转号码格式无效!\n例子:\n8613004602000\n86575xxxxxxxx')
        else:
            d = {'CFU': '无条件', 'CFB': '遇忙', 'CFNA': '无应答', 'CFNR': '无网络'}
            if n == 'E':
                if tkMessageBox.askokcancel('警告', '确认要取消 *' + d[v] + '* 呼转?'):
                    self.cfx_num = n
                    self.cfx_type = v
                    self.frame.destroy()
            else:
                if tkMessageBox.askokcancel('警告', '确认要 *' + d[v] + '* 呼转到 ' + n + ' ?'):
                    self.cfx_num = n
                    self.cfx_type = v
                    self.frame.destroy()


if __name__ == "__main__":
    f = CFxFrame()
    print f.cfx_num, f.cfx_type
