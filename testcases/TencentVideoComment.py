# !/usr/bin/env python
# coding: utf-8
"""
#!!================================================================
#版权 (C) 2023, Huawei Technologies Co.
#==================================================================
#文 件 名：                 TencentVideoComment.py
#文件说明：                 腾讯视频测试用例：打开应用，跳过广告，播放视频，查看评论并上划（评论区滑动）
#作    者：                 author
#生成日期：                 2025-12-11
#!!================================================================
"""

import time
from devicetest.core.test_case import Step
from hypium import *
from TencentVideoBase import TencentVideoBase


class TencentVideoComment(TencentVideoBase):
    def __init__(self, controllers):
        super().__init__(controllers)
        # 可自定义滑动次数，基准60次，压测时乘以 stress_multiplier
        self.swipe_count = 60 * self.stress_multiplier
        # pmap采样间隔时间（秒），默认1秒
        self.hidumper_interval = 1

    def setup(self):
        """调用父类的setup方法"""
        super().setup()

    def commentpageSlide(self):
        Step('4.选择首页第一个视频')
        self._click_first_video()

        Step('5.切换到评论')
        self._switch_to_comment()

        Step('6.评论区上划，每秒上划一次')
        self._slide_page(self.swipe_count, end_y_ratio=0.4, sleep_interval=0.1, memdump_remaining=8)

    def process(self):
        # 调用公共方法：强制退出app、启动pmap监控、启动应用、跳过广告
        self._start_app_with_monitor_and_skip_ad()
        self.commentpageSlide()

    def teardown(self):
        """调用父类的teardown方法"""
        super().teardown()

