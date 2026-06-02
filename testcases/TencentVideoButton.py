# !/usr/bin/env python
# coding: utf-8
"""
#!!================================================================
#版权 (C) 2023, Huawei Technologies Co.
#==================================================================
#文 件 名：                 TencentVideoButton.py
#文件说明：                 腾讯视频测试用例：打开应用，跳过广告，首页button切换（button切换）
#作    者：                 author
#生成日期：                 2025-12-11
#!!================================================================
"""

import time
from devicetest.core.test_case import Step
from hypium import *
from TencentVideoBase import TencentVideoBase


class TencentVideoButton(TencentVideoBase):
    def __init__(self, controllers):
        super().__init__(controllers)
        # pmap采样间隔时间（秒），默认1秒
        self.hidumper_interval = 1

    def setup(self):
        """调用父类的setup方法"""
        super().setup()

    def process(self):
        # 调用公共方法：强制退出app、启动pmap监控、启动应用、跳过广告
        self._start_app_with_monitor_and_skip_ad()

        Step('4.首页button来回切换')
        self._tab_switch(memdump_remaining=1)

    def teardown(self):
        """调用父类的teardown方法"""
        super().teardown()
