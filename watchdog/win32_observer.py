# -*- coding: utf-8 -*-

import win32file
import win32con

from os.path import realpath, abspath, sep as path_separator, join as path_join, isdir as path_isdir
from threading import Thread, Event as ThreadedEvent
from Queue import Queue
from polling_observer import PollingObserver, _Rule
from events import DirMovedEvent, DirDeletedEvent, DirCreatedEvent, DirModifiedEvent, \
    FileMovedEvent, FileDeletedEvent, FileCreatedEvent, FileModifiedEvent

from win32con import FILE_SHARE_READ, FILE_SHARE_WRITE, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, \
    FILE_NOTIFY_CHANGE_FILE_NAME, FILE_NOTIFY_CHANGE_DIR_NAME, FILE_NOTIFY_CHANGE_ATTRIBUTES, \
    FILE_NOTIFY_CHANGE_SIZE, FILE_NOTIFY_CHANGE_LAST_WRITE, FILE_NOTIFY_CHANGE_SECURITY
from win32file import ReadDirectoryChangesW



FILE_LIST_DIRECTORY = 0x0001
BUFFER_SIZE = 1024
FILE_NOTIFY_FLAGS = FILE_NOTIFY_CHANGE_FILE_NAME | FILE_NOTIFY_CHANGE_DIR_NAME | \
    FILE_NOTIFY_CHANGE_ATTRIBUTES | FILE_NOTIFY_CHANGE_SIZE | \
    FILE_NOTIFY_CHANGE_LAST_WRITE | FILE_NOTIFY_CHANGE_SECURITY

FILE_SHARE_FLAGS = FILE_SHARE_READ | FILE_SHARE_WRITE
    
FILE_ACTION_CREATED = 1
FILE_ACTION_DELETED = 2
FILE_ACTION_MODIFIED = 3
FILE_ACTION_RENAMED_OLD_NAME = 4
FILE_ACTION_RENAMED_NEW_NAME = 5

DIR_ACTION_EVENT_MAP = {
    FILE_ACTION_CREATED: DirCreatedEvent,
    FILE_ACTION_DELETED: DirDeletedEvent,
    FILE_ACTION_MODIFIED: DirModifiedEvent,
}
FILE_ACTION_EVENT_MAP = {
    FILE_ACTION_CREATED: FileCreatedEvent,
    FILE_ACTION_DELETED: FileDeletedEvent,
    FILE_ACTION_MODIFIED: FileModifiedEvent,
}


class _Win32EventEmitter(Thread):
    def __init__(self, path, out_event_queue, *args, **kwargs):
        Thread.__init__(self)
        self.stopped = ThreadedEvent()
        self.setDaemon(True)
        self.path = path
        self.out_event_queue = out_event_queue

    def stop(self):
        self.stopped.set()

    def run(self):
        handle_directory = win32file.CreateFile (
            self.path,
            FILE_LIST_DIRECTORY,
            FILE_SHARE_FLAGS,
            None,
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS,
            None
        )
        while not self.stopped.is_set():
            results = ReadDirectoryChangesW (
                handle_directory,
                BUFFER_SIZE,
                True,
                FILE_NOTIFY_FLAGS,
                None,
                None
                )
            last_renamed_from_filename = ""
            q = self.out_event_queue
            for action, filename in results:
                filename = path_join(self.path, filename)
                if action == FILE_ACTION_RENAMED_OLD_NAME:
                    last_renamed_from_filename = filename
                elif action == FILE_ACTION_RENAMED_NEW_NAME:
                    if path_isdir(filename):
                        q.put((self.path, DirMovedEvent(last_renamed_from_filename, filename)))
                    else:
                        q.put((self.path, FileMovedEvent(last_renamed_from_filename, filename)))
                else:
                    if path_isdir(filename):
                        action_event_map = DIR_ACTION_EVENT_MAP
                    else:
                        action_event_map = FILE_ACTION_EVENT_MAP
                    q.put((self.path, action_event_map[action](filename)))


class Win32Observer(PollingObserver):
    def _create_event_emitter(self, path):
        return _Win32EventEmitter(path=path, out_event_queue=self.event_queue)


if __name__ == '__main__':
    import time
    import sys

    from os.path import abspath, realpath, dirname
    from events import FileSystemEventHandler

    o = Win32Observer()
    event_handler = FileSystemEventHandler()
    o.schedule('arguments', event_handler, *sys.argv[1:])
    o.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        o.unschedule('arguments')
        o.stop()
    o.join()
