import uuid
import logging
logger = logging.getLogger(__name__) #__name___ = nombre del modulo. logging.getLogger = Usa la misma instancia de clase (del starter.py).
from collections import OrderedDict

#Libs
import cons


class DownloadItem:
    """"""
    def __init__(self, name, host, size, link, path=cons.DLFOLDER_PATH, can_copy_link=True): #ile_name, host, size, link
        """"""
        self.id = str(uuid.uuid1()) #id unico.
        self.path = path
        self.name = name
        self.link = link
        self.host = host
        self.link_status = cons.LINK_CHECKING
        self.link_status_msg = None
        self.status = cons.STATUS_QUEUE #download status
        self.status_msg = None
        self.progress = 0
        self.size = size
        self.size_complete = 0
        self.speed = 0
        self.time = 0
        self.time_remain = 0
        self.chunks = []
        self.fail_count = 0
        self.can_resume = False
        self.is_premium = False
        self.can_copy_link = can_copy_link

    def update(self, name, status, progress, size, size_complete, speed,
                time, time_remain, chunks, status_msg, can_resume, is_premium):
        """"""
        self.name = name
        self.status = status
        self.status_msg = status_msg
        self.progress = progress
        self.size = size
        self.size_complete = size_complete
        self.speed = speed
        self.time = time
        self.time_remain = time_remain
        self.chunks = chunks or []
        self.can_resume = can_resume
        self.is_premium = is_premium

    def set_path(self, path):
        """"""
        self.path = path

    def reset_fail_count(self):
        """"""
        self.fail_count = 0


class DownloadCore:
    """"""
    def __init__(self):
        """"""
        self.active_downloads = {}
        self.queue_downloads = OrderedDict()
        self.complete_downloads = {}
        self.stopped_downloads = {}
    
    def reorder_queue(self, id_order_list):
        """
        TODO: only replace the order list in OrderedDict.
        """
        ordered_items_dict = OrderedDict()
        for id_item in id_order_list:
            try:
                ordered_items_dict[id_item] = self.queue_downloads[id_item]
            except KeyError:
                pass
        if len(self.queue_downloads) == len(ordered_items_dict):
            self.queue_downloads.clear()
            self.queue_downloads.update(ordered_items_dict)
        else:
            logger.warning("reorder_queue failed")
    
    #def reorder_queue(self, id_order_list):
        #""""""
        #self.reorder_list(self.queue_downloads, id_order_list)
    
    def reorder_list(self, download_list, id_order_list):
        """
        binding: los cambios en la 'copia' de la lista se reflejan en la lista original.
        """
        ordered_items_list = []
        items_dict = dict([(download_item.id, download_item) for download_item in download_list])
        for id_item in id_order_list:
            try:
                ordered_items_list.append(items_dict[id_item])
            except KeyError:
                pass
        if len(download_list) == len(ordered_items_list):
            download_list[:] = ordered_items_list #reorder in-place
        else:
            logger.warning("reorder_list failed")


if __name__ == "__main__":
    pass
    
    
    
