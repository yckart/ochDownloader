
from PySide.QtGui import *
from PySide.QtCore import *

import core.cons as cons
from core.conf_parser import conf
from core.api import api


class StatusBar(QStatusBar):
    def __init__(self, parent=None):
        QStatusBar.__init__(self, parent)

        self.parent = parent
        self.update_manager = api.start_update_manager()

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox_widget = QWidget()
        hbox_widget.setLayout(hbox)
        self.addPermanentWidget(hbox_widget) #permanent widgets go to right.
        
        label_slots = QLabel(_('Slots limit:'))
        hbox.addWidget(label_slots)
        
        self.slots_box = QSpinBox()
        self.slots_box.setRange(1, 20)
        self.slots_box.valueChanged.connect(self.on_slots_changed)
        hbox.addWidget(self.slots_box)
        
        hbox.addSpacing(10)
        
        label_speed = QLabel(_('Speed limit:'))
        hbox.addWidget(label_speed)
        
        self.speed_box = QSpinBox()
        self.speed_box.setAccelerated(True)
        self.speed_box.setRange(0, 99999)
        self.speed_box.valueChanged.connect(self.on_speed_changed)
        hbox.addWidget(self.speed_box)
        
        # ####################### #
        
        self.msg_list = []
        
        self.push_msg(_('Update checking...'))
        self.timer = parent.idle_timeout(1000, self.update_check)

        self.on_load()
    
    def on_slots_changed(self, new_value):
        api.new_slot_limit(new_value)
    
    def on_speed_changed(self, new_value):
        api.bucket.rate_limit(new_value)
    
    def push_msg(self, msg):
        self.showMessage(msg)
        self.msg_list.append(msg)
    
    def pop_msg(self, msg):
        try:
            self.msg_list.remove(msg) #should remove the last ocurrence not the first...
        except ValueError:
            pass
        if self.currentMessage() == msg:
            try:
                self.showMessage(self.msg_list[-1])
            except IndexError:
                self.clearMessage()
    
    def push_timeout_msg(self, timeout, msg):
        self.showMessage(msg, timeout)

    def on_load(self):
        DEFAULT_SLOTS = 3
        self.slots_box.setValue(DEFAULT_SLOTS)
        api.new_slot_limit(DEFAULT_SLOTS)

    #temp
    def update_check(self):
        if self.update_manager.update_check_complete:
            if self.update_manager.update_available:
                self.pop_msg(_('Update checking...')) #eliminar mensaje anterior, sino se acumulan.
                self.push_msg(_("Update available"))
                #add links to check list.
                self.parent.add_downloads.links_checking(self.update_manager.url_update)
            else:
                self.pop_msg(_('Update checking...'))
            self.timer.stop()
