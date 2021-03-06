#!/usr/bin/env python
#
# -*- mode:python; sh-basic-offset:4; indent-tabs-mode:nil; coding:utf-8 -*-
# vim:set tabstop=4 softtabstop=4 expandtab shiftwidth=4 fileencoding=utf-8:
#
# Copyright (c) 2012, Jorge A Gallegos <kad@blegh.net>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import argparse
import boto
from dateutil import parser
import grp
import json
import logging
import threading
import os
import pwd
import socket
import sys
from Queue import Queue

log = logging.getLogger('tableslurp')
stderr = logging.StreamHandler()
stderr.setFormatter(logging.Formatter(
    '%(name)s [%(asctime)s] %(levelname)s %(message)s'))
log.addHandler(stderr)
if os.environ.get('TDEBUG', False):
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)


class DownloadCounter(object):
    filename = None
    attemptcount = 0

    def __init__(self, filename):
        self.filename = filename

    def increment(self):
        self.attemptcount += 1


class DownloadHandler(object):
    key = None
    secret = None
    bucket_name = None
    owner = None
    group = None
    preserve = False
    target = None
    origin = None
    prefix = None
    force = False
    name = socket.getfqdn()
    fileset = []
    queue = Queue()
    num_threads = 4
    threads = {}

    def __init__(self, args):
        self.target = args.target[0]
        self.origin = args.origin[0]
        self.preserve = args.preserve
        self.key = args.aws_key
        self.secret = args.aws_secret
        self.bucket_name = args.bucket[0]
        self.num_threads = args.threads
        self.force = args.force
        if args.name:
            self.name = args.name
        self.prefix = '%s:%s' % (self.name, self.origin)

#       It may be a bit sub-optimal, but I rather fail sooner than later
        (owner, group) = self._build_file_set(args.file)

        if not self.preserve:
            owner = args.owner
            group = args.group

        try:
            self.owner = pwd.getpwnam(owner).pw_uid
            self.group = grp.getgrnam(group).gr_gid
        except Exception as e:
            log.error(e)
            raise OSError('User/Group pair %s:%s does not exist' %
                (owner, group,))

    def _get_bucket(self):
#       unsure if boto is thread-safe, will reconnect every time
        log.debug('Connecting to s3')
        conn = boto.connect_s3(self.key, self.secret)
        bucket = conn.get_bucket(self.bucket_name)
        log.debug('Connected to s3')
        return bucket

    def _build_file_set(self, target_file=None):
        log.info('Building fileset')
        key = None
#       If you want to restore a file-set in particular
        bucket = self._get_bucket()
        if target_file:
            key = bucket.get_key('%s/%s-listdir.json' %
                (self.prefix, target_file))
#       Otherwise try to fetch the most recent one
        else:
            keys = [_ for _ in bucket.get_all_keys(prefix='%s/' %
                (self.prefix,)) if _.name.endswith('-listdir.json')]
            if keys:
                keys.sort(key=lambda l: parser.parse(l.last_modified))
                key = keys.pop()

        if not key:
            raise LookupError('Cannot find anything to restore from %s:%s/%s' %
                (bucket.name, self.prefix, target_file or ''))

        json_data = json.loads(key.get_contents_as_string())
        self.fileset = json_data[self.origin]
        log.info('Fileset contains %d files to download' % (len(self.fileset)))
        k = bucket.get_key('%s/%s' % (self.prefix, self.fileset[0]))
#       The librato branch introduced this
        meta = k.get_metadata('stat')
        log.debug('Metadata is %s' % (meta,))
        owner = None
        group = None
        if meta:
            try:
                json_data = json.loads(meta)
                owner = json_data['user']
                group = json_data['group']
            except TypeError as te:
                log.debug(te)
                log.warning('Could not parse stat metadata for %s' % (k.name,))
            except KeyError as ke:
                log.debug(ke)
                log.warning('Incomplete stat metadata for %s, will ignore' %
                    (k.name,))
        return (owner, group)

    def _test_permissions(self):
        log.info('Will now try to test writing to the target dir %s' %
            (self.target,))
        try:

            if os.path.isdir(self.target) == False:
                log.debug('Creating temp file in %s' % (self.target,))
                os.makedirs(self.target)
            log.debug('Changing owner:group for %s to %s:%s' %
                (self.target, self.owner, self.group,))

            os.chown(self.target, self.owner, self.group)
        except Exception as e:
            log.debug(e)
            log.exception('%s exists' % (self.target,))
        log.info('Will write to %s' % (self.target,))

    def _worker(self, idx, queue):
        log.info('Thread #%d processing items' % (idx, ))
        bucket = self._get_bucket()

        while queue.empty() == False:
            queueddownload = queue.get()
            fname = queueddownload.filename
            keypath = '%s/%s' % (self.prefix, fname,)
            destfile = os.path.join(self.target, os.path.basename(fname))

            log.debug('Checking if we need to download %s to %s' %
                (keypath, destfile,))

            if queueddownload.attemptcount < 5:
                download = False
                #Retry downloading until we succeed
                try:
                    key = bucket.get_key(keypath)
                    log.debug('Key objectd is %s' % key)
                    if os.path.isfile(destfile):
                        stat = os.stat(destfile)
                        if self.force:
                            download = True
                        elif stat.st_size != key.size:
                            log.info('%s and %s size differs, will '
                                're-download' % (key.name, destfile,))
                            download = True
                    else:
                        download = True

                    if download:
                        log.info('Downloading %s from %s to %s' %
                            (key.name, bucket.name, destfile))
                        key.get_contents_to_filename(destfile)

                except Exception as e:
                    log.debug(e)
                    log.exception('Failed to download `%s` retrying' %
                        (fname,))
                    #We can't download, try again
                    queueddownload.increment()
                    queue.put(queueddownload)

            else:
                log.info('Tried to download %s too many times.  Giving up' %
                    fname)

            #Pop the task regardless of state.  If it fails we've put it back
            queue.task_done()

        # log.info('Thread #%d finished processing' % (idx,))

    def run(self):
        self._test_permissions()
        log.info('Running')

        #queue up the filesets
        for filename in self.fileset:
            log.info('Pushing file %s onto queue' % filename)
            self.queue.put(DownloadCounter(filename))

#       launch threads and attach an event to them
        for idx in range(0, self.num_threads):
            self.threads[idx] = {}
#            e = threading.Event()
            t = threading.Thread(target=self._worker,
                kwargs={'idx': idx, 'queue': self.queue})
            t.setDaemon(True)
            self.threads[idx] = t
            t.start()

        #Wait for everything to finish downloading
        self.queue.join()
        log.info('My job is done.')


def main():
    p = pwd.getpwnam(os.environ['USER'])
    owner = p.pw_name
    group = [_.gr_name for _ in grp.getgrall() if _.gr_gid == p.pw_gid][0]
    ap = argparse.ArgumentParser(
        description='This is the companion script to the `tablesnap` program '
        'which you can use to restore files from an Amazon S3 bucket to any '
        'given local directory which you have write-permissions on. While the '
        'code is straightforward, the program assumes the files you are '
        'restoring got previously backed up with `tablesnap`',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('-k', '--aws-key',
        required=True, help='Amazon S3 key')
    ap.add_argument('-s', '--aws-secret',
        required=True, help='Amazon S3 secret')
    ap.add_argument('-p', '--preserve', default=False, action='store_true',
        help='Preserve the permissions (if they exist) from the source. '
        'This overrides -o and -g')
    ap.add_argument('-o', '--owner', default=owner,
        help='After download, chown files to this user.')
    ap.add_argument('-g', '--group', default=group,
        help='After download, chgrp files to this group.')
    ap.add_argument('-t', '--threads', type=int, default=4,
        help='Split the download between this many threads')
    ap.add_argument('-f', '--file',
        help='If specified, will download the file-set this file belongs to '
        'instead of the latest one available.')
    ap.add_argument('--force', default=False, action='store_true',
        help='Force download files even if they exist')
    ap.add_argument('-n', '--name', default=socket.getfqdn(),
        help='Use this name instead of the FQDN to prefix the bucket dir')
    ap.add_argument('bucket', nargs=1,
        help='S3 bucket to download files from')
    ap.add_argument('origin', nargs=1,
        help='Path inside the bucket to the directory you want to download '
        'files from')
    ap.add_argument('target', nargs=1,
        help='Path in the local FS where files should be downloaded to')
    args = ap.parse_args()
    dh = DownloadHandler(args)
    dh.run()

if __name__ == '__main__':
    sys.exit(main())