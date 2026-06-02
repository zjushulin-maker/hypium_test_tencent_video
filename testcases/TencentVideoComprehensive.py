# !/usr/bin/env python
# coding: utf-8
"""
#!!================================================================
#版权 (C) 2023, Huawei Technologies Co.
#==================================================================
#文 件 名：                 TencentVideoComprehensive.py
#文件说明：                 腾讯视频综合测试用例：首页button切换、视频播放滑动、评论区滑动
#作    者：                 author
#生成日期：                 2025-12-24
#!!================================================================
"""

import time
from devicetest.core.test_case import Step
from hypium import *
from TencentVideoBase import TencentVideoBase


class TencentVideoComprehensive(TencentVideoBase):
    def __init__(self, controllers):
        super().__init__(controllers)
        # button列表由基类统一定义，如需自定义可在此覆盖
        # 视频滑动次数，基准20次，压测时乘以 stress_multiplier
        self.video_swipe_count = 20 * self.stress_multiplier
        # 评论区滑动次数，基准50次，压测时乘以 stress_multiplier
        self.comment_swipe_count = 50 * self.stress_multiplier
        # pmap采样间隔时间（秒），默认1秒
        self.hidumper_interval = 1

    def setup(self):
        """调用父类的setup方法"""
        super().setup()

    def process(self):
        # 调用公共方法：强制退出app、启动pmap监控、启动应用、跳过广告
        self._start_app_with_monitor_and_skip_ad()

        Step('4.首页button切换一次（来回）')
        self._tab_switch()

        Step('5.选择首页第一个视频')
        self._click_first_video()

        Step('6.视频播放界面向上滑动20秒')
        self._slide_page(self.video_swipe_count, end_y_ratio=0.3, sleep_interval=0.3)

        Step('8.切换到评论')
        self._switch_to_comment()

        Step('9.评论区上划50秒')
        self._slide_page(self.comment_swipe_count, end_y_ratio=0.3, sleep_interval=0.2, memdump_remaining=11)

    def teardown(self):
        """调用父类的teardown方法"""
        super().teardown()

