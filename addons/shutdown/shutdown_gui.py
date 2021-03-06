
from shutdown import Shutdown
import core.cons as cons
from core.events import events

from PySide.QtGui import *
from PySide.QtCore import *

if cons.OS_WIN:
    from qt.misc import flash_wnd

TIME_OUT = 60


class ShutdownDlg(QMessageBox):
    def __init__(self, parent):
        QMessageBox.__init__(self, parent)
        self.setWindowTitle(_('Shutting down'))
        
        self.setIconPixmap(QPixmap('ochdownload2.png'))
        
        self.setText(_("The system is going to shut down."))
        
        self.setStandardButtons(QMessageBox.Cancel)
        self.setDefaultButton(QMessageBox.Cancel)
        #self.setEscapeButton(QMessageBox.Cancel)
        
        self.timeout = TIME_OUT
        
        self.timer = parent.idle_timeout(1000, self.update)

        #Flash if the window is in the background.
        if cons.OS_WIN:
            flash_wnd.flash_taskbar_icon(parent.winId())
    
    def run(self):
        #Flash if the window is in the background.
        #if cons.OS_WIN:
            #flash_wnd.flash_taskbar_icon(parent.window.handle)
        ret_code = self.exec_()
        if ret_code in (QMessageBox.Cancel, QMessageBox.Close, QMessageBox.NoButton):
            self.timer.stop()
    
    def update(self):
        if self.timeout > 0:
            self.timeout -= 1
            self.setInformativeText(_("Shutting in") + " {0}".format(self.timeout))
        else:
            shutdown = Shutdown()
            if shutdown.start_shutting():
                events.trigger_quit()
    
    
