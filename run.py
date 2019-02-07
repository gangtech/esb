#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = "rengang"
import os
import tornado
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import tornado.escape
import tornado.autoreload
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
from tornado.options import define, options
from tornado.web import RequestHandler, gen
from tornado.httpclient import AsyncHTTPClient
from tornado.locks import Semaphore
import json
import time
import datetime
import subprocess
import uuid
import motor
import pprint
from pymongo import ReturnDocument

os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'
os.environ['LC_ALL'] = 'zh_CN.GBK'
os.environ['LANG'] = 'zh_CN.GBK'
define("port", default=5555, help="run on the given port", type=int)
define("debug", default=True, help="Debug Mode", type=bool)

mclient = motor.motor_tornado.MotorClient()


class phand_test(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.set_header('Access-Control-Max-Age', 1000)
        self.set_header('Access-Control-Allow-Headers', '*')

    @gen.coroutine
    def get(self):
        try:
            retcode = "1"
            message = ""
            iid = str(uuid.uuid4()).replace('-', '').lower()
            ixd = yield self.get_task(iid)
            if not iid == ixd:
                return self.write(retcode + " task_id {0} created failure".format(iid))
            bin_path = os.path.join(os.path.dirname(__file__), "bin", "esb_core.py")
            if not os.path.exists(bin_path):
                return self.write(retcode + " bin_path<{0}> not found".format(bin_path))
            cwd = os.path.dirname(bin_path)
            ymd = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            cmd = "nohup python {0} {1} >>/dev/null 2>&1 &".format(bin_path, iid)
            p = subprocess.Popen(cmd, cwd=cwd, shell=True)
            rec = yield self.query_task(iid)
            if rec["status"] == "0" or rec["status"] == None:
                return self.write("{0} timeout when exec status<{1}>".format(retcode,rec["status"]))
            retcode = "0"
        except Exception as ex:
            message += str(ex)
            retcode = "1"
        self.write("{0} {1} {2} {3}".format(retcode, ymd, iid, message))

    @gen.coroutine
    def get_task(self, task_id):
        mclient = self.settings["mclient"]
        tasks = mclient.esb.tasks
        # cur = yield tasks.find_one_and_update(filter={'_id':task_id,},update={"$set":{'status':"0"}},upsert=False,return_document=ReturnDocument.AFTER)
        cur = yield tasks.insert_one({"_id": task_id, "status": "0"})
        if cur:
            return cur.inserted_id

    @gen.coroutine
    def query_task(self, task_id):
        yield gen.sleep(5)
        mclient = self.settings["mclient"]
        tasks = mclient.esb.tasks
        cur = yield tasks.find_one({"_id": task_id})
        #print(json.dumps(cur))
        return cur


class phand_index(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.set_header('Access-Control-Max-Age', 1000)
        self.set_header('Access-Control-Allow-Headers', '*')

    def get(self):
        self.write('running')


def make_app():
    settings = dict(
        cookie_secret="61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
        gzip=True,
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        xsrf_cookies=False,
        debug=True,
        mclient=mclient,
    )
    handlers = [
        (r'/', phand_index),
        (r'/test', phand_test),
    ]
    return tornado.web.Application(handlers, default_handler_class=phand_index, **settings)


if __name__ == "__main__":
    tornado.options.parse_command_line()
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()
