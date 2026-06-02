# !/usr/bin/env python
# coding: utf-8
"""
#!!================================================================
#版权 (C) 2023, Huawei Technologies Co.
#==================================================================
#文 件 名：                 TencentVideoHome.py
#文件说明：                 腾讯视频测试用例：打开应用，跳过广告，首页滑动（首页滑动）
#作    者：                 author
#生成日期：                 2025-12-11
#!!================================================================
"""

import time
from devicetest.core.test_case import Step
from hypium import *
from TencentVideoBase import TencentVideoBase


class TencentVideoHome(TencentVideoBase):
    def __init__(self, controllers):
        super().__init__(controllers)
        # 可自定义滑动次数，基准20次，压测时乘以 stress_multiplier
        self.swipe_count = 50 * self.stress_multiplier
        # pmap采样间隔时间（秒），默认1秒
        self.hidumper_interval = 1

    def setup(self):
        """调用父类的setup方法"""
        super().setup()

    def process(self):
        # 调用公共方法：强制退出app、启动pmap监控、启动应用、跳过广告
        self._start_app_with_monitor_and_skip_ad()

        Step('4.首页上划，每秒上划一次')
        self._slide_page(self.swipe_count, end_y_ratio=0.2, sleep_interval=0.3, memdump_remaining=10)

    def teardown(self):
        """调用父类的teardown方法"""
        super().teardown()

