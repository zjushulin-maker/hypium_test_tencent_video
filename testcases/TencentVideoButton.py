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
import subprocess
from devicetest.core.test_case import Step
from hypium import *
from TencentVideoBase import TencentVideoBase


class TencentVideoButton(TencentVideoBase):
    def __init__(self, controllers):
        super().__init__(controllers)
        # 可自定义切换次数，默认2次（来回算一次）
        self.switch_count = 2
        # button列表
        self.button_list = ["首页", "电视剧", "动漫", "电影", "综艺", "NBA", "纪录片", "体育", "播客"]
        # pmap采样间隔时间（秒），默认1秒
        self.hidumper_interval = 1

    def setup(self):
        """调用父类的setup方法"""
        super().setup()

    def _click_button(self, button_name):
        """点击指定的button，使用BY.text().type("Button")的方式"""
        try:
            # 使用BY.text().type("Button")的方式点击button
            self.driver.touch(BY.text(button_name).type("Button"))
            return True
        except:
            try:
                # 如果失败，尝试只使用text查找
                button_element = self.driver.find_element(By.text(button_name))
                button_element.click()
                return True
            except:
                try:
                    # 如果By不存在，尝试直接通过文本查找
                    button_element = self.driver.find_element_by_text(button_name)
                    button_element.click()
                    return True
                except:
                    try:
                        # 如果都失败，使用CONTAINS模糊匹配，不限制类型
                        self.driver.touch(BY.text(button_name, MatchType.CONTAINS))
                        return True
                    except:
                        return False

    def process(self):
        # 调用公共方法：强制退出app、启动pmap监控、启动应用、跳过广告
        self._start_app_with_monitor_and_skip_ad()

        Step('4.首页button来回切换')
        # 来回切换指定次数，每次间隔1秒
        for i in range(self.switch_count):
            remaining = self.switch_count - i - 1  # 剩余次数
            
            # 当开关开启且剩余1次时，触发gc dump
            if self.enable_memdump and remaining == 1:
                Step('5.执行hdc shell命令触发gc dump')
                # 执行hdc shell命令写入control.log
                command1 = 'hdc shell \'echo "1" > /data/app/el2/100/base/com.tencent.videohm/files/control.log\''
                subprocess.run(command1, shell=True)
                time.sleep(1)
            
            # 顺序点击button
            for button_name in self.button_list:
                if self._click_button(button_name):
                    time.sleep(1.3)
                else:
                    # 如果找不到button，等待一下继续
                    time.sleep(1)
            
            # 逆序点击button
            for button_name in reversed(self.button_list):
                if self._click_button(button_name):
                    time.sleep(1.3)
                else:
                    # 如果找不到button，等待一下继续
                    time.sleep(1)

    def teardown(self):
        """调用父类的teardown方法"""
        super().teardown()

