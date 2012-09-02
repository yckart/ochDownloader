import urllib2
import httplib #httplib.HTTPException
import socket
import time
import threading
import logging
logger = logging.getLogger(__name__)

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from core.conf_parser import conf
from connection import URLClose, request
from downloader_core import DownloaderCore


NT_BUFSIZ = 8 * 1024 #8K. Network buffer.
#MAX_CONN = 10 #0 to 9
DATA_BUFSIZ = 64 * 1024 #64K.
START, END = range(2)


class BadSource(Exception): pass
class CanNotRun(Exception): pass
class IncompleteChunk(Exception): pass
class CanNotResume(Exception): pass


class MultiDownload(DownloaderCore):
    """"""
    def __init__(self, file_name, path_to_save, link, host, bucket, chunks):
        """"""
        DownloaderCore.__init__(self, file_name,  path_to_save, link, host, bucket)

        #Threading stuff
        self.lock1 = threading.Lock() #lock to write file.
        self.lock2 = threading.Lock()
        self.lock3 = threading.Lock()

        self.chunks = chunks[:] if chunks is not None else [] #shallow copy
        self.chunks_control = []

        self.first_flag = True
        self.conn_count = 0

        self.max_conn = conf.get_max_conn()

    def get_chunk_n_size(self):
        with self.lock2:
            return self.chunks[:], self.size_complete

    def get_conn_count(self):
        with self.lock3:
            return self.conn_count

    def spawn_thread(self, fh, i, chunk):
        th = threading.Thread(group=None, target=self.thread_download, name=None, args=(fh, i, chunk, self.first_flag))
        th.start()
        self.first_flag = False
        return th

    def create_chunks(self):
        chunk_size = (self.size_file / self.max_conn) + (self.size_file % self.max_conn)
        chunk_size = ((chunk_size / NT_BUFSIZ) + 1) * NT_BUFSIZ #proximo numero al tamanio del chunk que sea multiplo del buffer
        chunks = []
        start = 0
        while True:
            end = start + chunk_size if (start + chunk_size) < self.size_file else self.size_file
            chunks.append((start, end))
            start += chunk_size
            if end == self.size_file:
                break
        return chunks

    def __get_chunks_size_complete(self):
        complete = 0
        tmp = 0
        for chunk_tup in self.chunks:
            complete += chunk_tup[START] - tmp
            tmp = chunk_tup[END]
        return complete

    def threaded_download_manager(self, fh):
        if not self.chunks:
            self.chunks = self.create_chunks()
        else: #resume
            self.size_complete = self.__get_chunks_size_complete()
            self.size_tmp = self.size_complete

        self.chunks_control = [True for _ in self.chunks] #can_run

        th_list = [self.spawn_thread(fh, i, chunk) for i, chunk in enumerate(self.chunks[:])
                   if not chunk[END] or chunk[START] < chunk[END]] #end may be 0

        for th in th_list:
            th.join()

    def is_chunk_complete(self, chunk, complete):
        content_len = 0
        if self.size_file and self.size_file > chunk[START]:
            content_len = chunk[END] - chunk[START]
            logger.debug("downloaded {0} of {1}".format(complete, content_len))

        if content_len and complete < content_len:
            return False
        return True

    def get_source(self, chunk, is_first):
        if is_first:
            return self.source
        else:
            return request.get(self.link_file, cookie=self.cookie, range=(chunk[START], None))

    def dl_next_chunk(self, chunk, i):
        with self.lock2: #safe.
            with self.lock3:
                try:
                    if self.chunks_control[i] and chunk[END] == self.chunks[i][START]: #on resume, end from the current segment must be equal to start from the next one.
                        self.chunks_control[i] = False
                        chunk = (chunk[START], self.chunks[i][END]) #in case chunk[START] > self.chunks[i_][START] ?
                    elif not self.chunks_control[i]:
                        raise CanNotRun('Next chunk is downloading')
                    else:
                        raise CanNotResume('Can not resume next chunk')
                except IndexError:
                    raise CanNotRun('No more chunks left')
        return chunk

    def set_err(self, err):
        logger.exception(err)
        self.error_flag = True
        self.status_msg = "Error: {0}".format(err)

    def flush_buffer(self, fh, i, chunk, complete, buf, len_buf):
        try:
            with self.lock1:
                fh.seek(chunk[START] + complete - len_buf)
                fh.write(buf.getvalue())
            with self.lock2:
                self.chunks[i] = (chunk[START] + complete, self.chunks[i][END])
            buf.close()
        except ValueError as err:
            logger.warning(err)
        except EnvironmentError as err:
            self.set_err(err)

    def thread_download(self, fh, i, chunk, is_first):
        #first thread wont retry.
        #downloading chunk wont retry.
        #not downloading and not first should retry.
        is_downloading = False
        buf = StringIO()
        len_buf = 0
        complete = 0

        #for retry in range(3):
        try:
            with URLClose(self.get_source(chunk, is_first)) as s:
                #logger.debug(s.headers)
                if not is_first and not self.is_valid_range(s, chunk[START]):
                    raise BadSource('Link expired, or cant download the requested range.')

                with self.lock3:
                    if self.chunks_control[i]:
                        self.chunks_control[i] = False
                        self.conn_count += 1
                        is_downloading = True
                    elif not is_downloading: #may be retrying
                        raise CanNotRun('Another thread has taken over this chunk.')

                while True:
                    data = s.read(NT_BUFSIZ)
                    len_data = len(data)

                    buf.write(data)
                    len_buf += len_data
                    complete += len_data

                    if len_buf >= DATA_BUFSIZ:
                        self.flush_buffer(fh, i, chunk, complete, buf, len_buf)
                        buf = StringIO()
                        len_buf = 0

                    with self.lock2:
                        self.size_complete += len_data

                    if self.bucket.fill_rate: #self.bucket.fill_rate != 0
                        time.sleep(self.bucket.consume(len_data))

                    if self.stop_flag or self.error_flag:
                        return

                    if not len_data or (chunk[END] and complete >= (chunk[END] - chunk[START])): #end may be 0
                        if not self.is_chunk_complete(chunk, complete):
                            raise IncompleteChunk('Incomplete chunk')
                        logger.debug("complete {0} {1}".format(chunk[START], chunk[END]))
                        chunk = self.dl_next_chunk(chunk, i + 1)
                        logger.debug("keep dl {0} {1}".format(chunk[START], chunk[END]))
                        i += 1

        except (IncompleteChunk, CanNotResume) as err:
            #first included
            #propagate
            self.set_err(err)
            return
        except (BadSource, CanNotRun) as err:
            #not first (CanNotRun does not matter)
            #do not propagate
            logger.debug(err)
            return
        except (urllib2.URLError, httplib.HTTPException, socket.error) as err:
            if is_first or is_downloading:
                #propagate
                self.set_err(err)
            else:
                logger.debug(err)
                #retry?
            return
        except EnvironmentError as err:
            #propagate
            self.set_err(err)
            return
        finally:
            self.flush_buffer(fh, i, chunk, complete, buf, len_buf)


if __name__ == "__main__":
    pass
