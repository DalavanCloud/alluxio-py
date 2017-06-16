#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script starts {nprocess} python processes in parallel, each process runs
read.py to read a file stream from Alluxio and write it to a local file unique for
each process.

By default, each python process has an ID, starting from 0, for each process,
the Alluxio file is written to local filesystem {root}/{ID}.txt, the log of
each python process is logs/{start time of this script}-{ID}.txt.

This script should be run directly under its parent directory.
"""

import argparse
from multiprocessing import Process
import os
import shutil
import sys
import time

import syspath
import alluxio
from read import read


script_start_time = '-'.join(time.ctime().split(' '))

parser = argparse.ArgumentParser(
    description='Start multiple python processes to read a Alluxio file in parallel')
parser.add_argument('--nprocess', type=int, default=1,
                    help='number of python processes, each process runs read.py')
parser.add_argument('--root', required=True,
                    help='the local filesystem directory to store the files read from Alluxio')
parser.add_argument('--host', default='localhost',
                    help='Alluxio proxy server hostname')
parser.add_argument('--port', type=int, default=39999,
                    help='Alluxio proxy server web port')
parser.add_argument('--src', required=True,
                    help='path to the Alluxio file source')
parser.add_argument('--iteration', type=int, default=1,
                    help='number of iterations to repeat the concurrent reading')
args = parser.parse_args()

try:
    os.mkdir('logs')
except OSError:
    # logs already exists.
    pass


def run_read(process_id):
    log = 'logs/%s-%d.txt' % (script_start_time, process_id)
    dst = '%s/%d.txt' % (args.root, process_id)
    sys.stdout = open(log, 'w')
    read(args.host, args.port, args.src, dst)


total_time = 0
for iteration in xrange(args.iteration):
    print 'Iteration %d' % iteration
    os.mkdir(args.root)

    start_time = time.time()
    processes = []
    for i in xrange(args.nprocess):
        p = Process(target=run_read, args=(i,))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()
    total_time += time.time() - start_time

    if iteration < args.iteration - 1:
        shutil.rmtree(args.root)


client = alluxio.Client(args.host, args.port)
src_bytes = client.get_status(args.src).length
average_time = total_time / args.iteration
average_throughput = src_bytes / average_time

print 'Number of iterations: %d' % args.iteration
print 'Number of processes per iteration: %d' % args.nprocess
print 'File size: %d bytes' % src_bytes
print 'Total time: %f seconds' % total_time
print 'Average time for each iteration: %f seconds' % average_time
print 'Average read throughput: %f bytes/second' % average_throughput
