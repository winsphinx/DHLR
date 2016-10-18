#!/usr/bin/env python
# -*- coding: utf-8 -*-

import Tkinter
import tkMessageBox


class CFxFrame(object):

    def __init__(self):
        self.cfx_num = ''
        self.cfx_type = ''
        self.frame = Tkinter.Tk()
        self.frame.title('CFx')
        self.var = Tkinter.StringVar()
        self.var.set('CFU')
        self.num = Tkinter.Entry(self.frame, text="num, or blank to cancel")
        self.num.focus_set()
        for o, i in enumerate(['CFU', 'CFB', 'CFNA', 'CFNR']):
            Tkinter.Radiobutton(self.frame,
                                text=i,
                                variable=self.var,
                                value=i).grid(row=0, column=o)
        Tkinter.Label(self.frame, text='号码: ').grid(row=1, column=0)
        self.num.grid(row=1, column=1, columnspan=2, sticky=Tkinter.EW)
        Tkinter.Button(self.frame,
                       text='OK',
                       command=self.ok_clicked).grid(row=1, column=3)
        self.frame.mainloop()

    def num_validated(self, num):
        if num.isdigit() and num.startswith('86') or num == 'E':
            return True
        else:
            return False

    def ok_clicked(self):
        n = self.num.get().strip() or 'E'
        v = self.var.get().strip()
        if not self.num_validated(n):
            tkMessageBox.showinfo('警告', '号码无效!')
        else:
            self.cfx_num = n
            self.cfx_type = v
            self.frame.destroy()


if __name__ == "__main__":
    f = CFxFrame()
    print f.cfx_num, f.cfx_type
