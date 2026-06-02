# !/usr/bin/env python
# coding: utf-8
"""
#!!================================================================
#版权 (C) 2023, Huawei Technologies Co.
#==================================================================
#文 件 名：                 TencentVideoBase.py
#文件说明：                 腾讯视频测试用例基类，包含公共功能
#作    者：                 author
#生成日期：                 2025-12-24
#!!================================================================
"""

import time
import subprocess
import os
import threading
import re
from pathlib import Path
from devicetest.core.test_case import TestCase, Step
from hypium import *

# 压测倍率：所有子类的操作次数将乘以此值
# 1 = 正常模式，50 = 压测模式（操作次数变为原来的50倍）
STRESS_MULTIPLIER = 1


class TencentVideoBase(TestCase):
    """腾讯视频测试用例基类，包含公共功能"""
    def __init__(self, controllers):
        self.TAG = self.__class__.__name__
        TestCase.__init__(self, self.TAG, controllers)
        self.driver = UiDriver(self.device1)
        self.package_name = "com.tencent.videohm"
        # 压测倍率，子类操作次数初始化时乘以此值
        self.stress_multiplier = STRESS_MULTIPLIER
        # 首页button列表，子类可按需覆盖
        self.button_list = ["首页", "电视剧", "动漫", "电影", "综艺", "NBA", "纪录片", "体育", "播客", "游戏", "短视频", "宠物tv"]
        # memdump相关操作开关，默认开启
        self.enable_memdump = True
        # profiler相关操作开关，默认开启
        self.enable_profiler = False
        # pmap采样间隔时间（秒），默认1秒
        self.hidumper_interval = 1
        # 存储pmap采样数据：[(timestamp, virtual_mem_kb, physical_mem_kb), ...]
        self.hidumper_data = []
        # 用于控制pmap采样线程的标志
        self.hidumper_running = False
        self.hidumper_thread = None

    def setup(self):
        """公共setup方法，子类可以重写"""
        Step('1.检查并关闭腾讯视频应用（如果已打开）')
        # 检查应用是否在运行，如果运行则关闭
        try:
            # 尝试停止应用，如果应用未运行会抛出异常，忽略即可
            self.driver.stop_app(self.package_name)
            time.sleep(0.5)
        except:
            # 应用未运行，忽略异常
            pass
        
        # 只有当enable_memdump为True时才重置control.log
        if self.enable_memdump:
            # 执行hdc shell命令重置control.log
            command = f'hdc shell \'echo "0" > /data/app/el2/100/base/{self.package_name}/files/control.log\''
            subprocess.run(command, shell=True)
            time.sleep(0.5)
        
        # 如果开启profiler，在启动app前清理并启动profiler
        if self.enable_profiler:
            Step('1.1.清理hiprofiler_data.htrace文件')
            # 清理hiprofiler_data.htrace文件
            command_clean = 'hdc shell "rm -f /data/local/tmp/hiprofiler_data.htrace"'
            subprocess.run(command_clean, shell=True)
            time.sleep(0.5)
            
            Step('1.2.启动hiprofiler')
            # 执行hiprofiler_cmd命令
            hiprofiler_cmd = f'''hdc shell "hiprofiler_cmd \\
  -c - \\
  -o /data/local/tmp/hiprofiler_data.htrace \\
  -t 60 \\
  -s \\
  -k \\
<<CONFIG
 request_id: 1
 session_config {{
  buffers {{
   pages: 131072
  }}
 }}
 plugin_configs {{
  plugin_name: \\"nativehook\\"
  sample_interval: 5000
  config_data {{
   save_file: false
   smb_pages: 16384
   max_stack_depth: 20
   process_name: \\"{self.package_name}\\"
   string_compressed: true
   fp_unwind: true
   blocked: true
   callframe_compress: true
   record_accurately: true
   offline_symbolization: true
   statistics_interval: 1
   startup_mode: true
  }}
 }}
CONFIG"'''
            # 在后台执行hiprofiler命令
            subprocess.Popen(hiprofiler_cmd, shell=True)
            time.sleep(1)

    def _parse_pmap_kotlin_memory(self, output_line):
        """从shell命令输出中解析anon:Kotlin的内存信息，返回(虚拟内存总和, 物理内存总和)，单位kB
        输入格式：'virtual_sum physical_sum' 或 '0 0'（未找到时）
        """
        try:
            parts = output_line.strip().split()
            if len(parts) >= 2:
                virtual_mem = int(parts[0])
                physical_mem = int(parts[1])
                return (virtual_mem, physical_mem)
            return None
        except (ValueError, IndexError) as e:
            print(f"解析pmap输出失败: {e}, 输出: {output_line}")
            return None
    
    def _hidumper_monitor_thread(self):
        """后台线程：定期执行pmap命令并解析anon:Kotlin内存信息"""
        while self.hidumper_running:
            # 记录本次循环开始时间
            loop_start_time = time.time()
            
            try:
                # 在执行pmap命令之前记录时间戳，确保反映实际内存状态的时间点
                # 使用微秒级时间戳（整数格式）
                timestamp = int(time.time() * 1000000)
                
                # 在设备端完成所有处理，返回两个数字（虚拟内存总和 物理内存总和）
                # 使用shell脚本在设备端完成提取和求和，避免Python端处理大量数据
                # 使用临时文件避免子shell变量丢失问题
                command_pmap = f"""hdc shell 'pid=$(pidof {self.package_name}); if [ -n "$pid" ]; then tmp=$(mktemp 2>/dev/null || echo /data/local/tmp/pmap_tmp_$$); pmap -x $pid 2>/dev/null | grep "CMCGC" | sed "s/^[^ ]* *\\([0-9]*\\) *\\([0-9]*\\).*/\\1 \\2/" > $tmp; virtual=0; physical=0; while read kbytes rss rest; do [ -n "$kbytes" ] && [ -n "$rss" ] && virtual=$((virtual + kbytes)) && physical=$((physical + rss)); done < $tmp; rm -f $tmp 2>/dev/null; echo "$virtual $physical"; else echo "0 0"; fi'"""
                
                # 对于0.5秒间隔，设置超时为1秒（2倍间隔），如果超过说明有问题
                cmd_timeout = max(1.0, self.hidumper_interval * 2)
                result = subprocess.run(command_pmap, shell=True, capture_output=True, text=True, timeout=cmd_timeout)
                
                if result.returncode == 0:
                    # 解析输出，应该只有一行：'virtual_sum physical_sum'
                    output_line = result.stdout.strip()
                    if output_line:
                        kotlin_mem = self._parse_pmap_kotlin_memory(output_line)
                        if kotlin_mem is not None:
                            virtual_mem, physical_mem = kotlin_mem
                            # 保存时间戳、虚拟内存和物理内存
                            self.hidumper_data.append((timestamp, virtual_mem, physical_mem))
                            # 每10次采样打印一次，避免输出过多
                            if len(self.hidumper_data) % 10 == 1:
                                print(f"[Pmap Monitor] 已采集 {len(self.hidumper_data)} 个数据点，最新: 时间={timestamp}, 虚拟内存={virtual_mem} kB, 物理内存={physical_mem} kB")
                        else:
                            print(f"[Pmap Monitor] 未能解析输出: {output_line}")
                    else:
                        # 没有输出，记录为0（可能是进程还未启动）
                        self.hidumper_data.append((timestamp, 0, 0))
                        if len(self.hidumper_data) <= 5:  # 前5次如果没有数据，打印提示
                            print(f"[Pmap Monitor] 警告: 未找到anon:Kotlin内存信息 (可能是应用还未启动), 时间={timestamp}")
                else:
                    # 命令执行失败，记录为0
                    self.hidumper_data.append((timestamp, 0, 0))
                    if result.stderr:
                        print(f"[Pmap Monitor] pmap命令执行失败: {result.stderr}, 时间={timestamp}")
            except subprocess.TimeoutExpired:
                print(f"[Pmap Monitor] pmap命令超时")
            except Exception as e:
                print(f"[Pmap Monitor] 执行pmap命令时出错: {e}")
            
            # 计算本次循环实际耗时
            loop_elapsed = time.time() - loop_start_time
            # 计算需要等待的时间，确保采样间隔尽量接近设定值
            sleep_time = self.hidumper_interval - loop_elapsed
            # 如果实际耗时已经超过设定间隔，则立即进行下一次采样（不等待）
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # 如果处理时间已经超过设定间隔，打印警告信息
                if loop_elapsed > self.hidumper_interval * 1.1:  # 超过10%才警告
                    print(f"[Pmap Monitor] 警告: 处理耗时 {loop_elapsed:.3f}s 超过设定间隔 {self.hidumper_interval}s")
    
    def _start_hidumper_monitor(self):
        """启动pmap监控线程"""
        if self.hidumper_interval > 0:
            self.hidumper_running = True
            self.hidumper_data = []
            self.hidumper_thread = threading.Thread(target=self._hidumper_monitor_thread, daemon=True)
            self.hidumper_thread.start()
            print(f"[Pmap Monitor] 已启动，采样间隔: {self.hidumper_interval}秒")
    
    def _stop_hidumper_monitor(self):
        """停止pmap监控线程"""
        if hasattr(self, 'hidumper_running') and self.hidumper_running:
            self.hidumper_running = False
            if self.hidumper_thread and self.hidumper_thread.is_alive():
                self.hidumper_thread.join(timeout=5)
            print(f"[Pmap Monitor] 已停止，共采集 {len(self.hidumper_data)} 个数据点")
        elif hasattr(self, 'hidumper_data'):
            print(f"[Pmap Monitor] 监控未启动或已停止，共采集 {len(self.hidumper_data)} 个数据点")

    # ==================== 公共页面操作方法 ====================

    def _click_button(self, button_name):
        """点击指定的button，使用BY.text().type("Button")的方式
        Args:
            button_name: button文本名称
        Returns:
            bool: 是否点击成功
        """
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

    def _slide_page(self, swipe_count, start_y_ratio=0.7, end_y_ratio=0.2, sleep_interval=0.3, slide_time=0.3, memdump_remaining=None):
        """通用页面滑动方法
        Args:
            swipe_count: 滑动次数
            start_y_ratio: 起始Y坐标比例（0-1），默认0.7
            end_y_ratio: 结束Y坐标比例（0-1），默认0.2
            sleep_interval: 每次滑动后等待时间（秒），默认0.3
            slide_time: 单次滑动持续时间（秒），默认0.3
            memdump_remaining: 当剩余次数等于此值时触发gc dump，None表示不触发
        """
        window_size = self.driver.get_window_size()
        width = window_size[0]  # tuple的第一个元素是width
        height = window_size[1]  # tuple的第二个元素是height
        start_x = int(width * 0.5)
        start_y = int(height * start_y_ratio)
        end_x = int(width * 0.5)
        end_y = int(height * end_y_ratio)

        for i in range(swipe_count):
            remaining = swipe_count - i - 1  # 剩余次数

            # 当开关开启且剩余次数匹配时，触发gc dump
            if memdump_remaining is not None and self.enable_memdump and remaining == memdump_remaining:
                Step('执行hdc shell命令触发gc dump')
                command1 = f'hdc shell \'echo "1" > /data/app/el2/100/base/{self.package_name}/files/control.log\''
                subprocess.run(command1, shell=True)
                time.sleep(1)

            # 执行滑动
            self.driver.slide((start_x, start_y), (end_x, end_y), slide_time=slide_time)
            time.sleep(sleep_interval)

    def _tab_switch(self, switch_count=1, forward_sleep=1.3, backward_sleep=0.8, fail_sleep=0.5, memdump_remaining=None):
        """首页button来回切换
        Args:
            switch_count: 来回切换次数（来回算一次），默认3次
            forward_sleep: 顺序点击成功时每次间隔（秒），默认0.8
            backward_sleep: 逆序点击成功时每次间隔（秒），默认0.8
            fail_sleep: 点击失败时等待时间（秒），默认0.5
            memdump_remaining: 当剩余次数等于此值时触发gc dump，None表示不触发
        """
        for i in range(switch_count):
            remaining = switch_count - i - 1  # 剩余次数

            # 当开关开启且剩余次数匹配时，触发gc dump
            if memdump_remaining is not None and self.enable_memdump and remaining == memdump_remaining:
                Step('执行hdc shell命令触发gc dump')
                command1 = f'hdc shell \'echo "1" > /data/app/el2/100/base/{self.package_name}/files/control.log\''
                subprocess.run(command1, shell=True)
                time.sleep(1)

            # 顺序点击button
            for button_name in self.button_list:
                if self._click_button(button_name):
                    time.sleep(forward_sleep)
                else:
                    time.sleep(fail_sleep)

            # 逆序点击button
            for button_name in reversed(self.button_list):
                if self._click_button(button_name):
                    time.sleep(backward_sleep)
                else:
                    time.sleep(fail_sleep)

    def _click_first_video(self, position=(334, 1450)):
        """点击首页第一个视频
        Args:
            position: 视频位置坐标，默认(334, 1450)
        """
        self._click_button("电视剧")
        time.sleep(1)  # 等待视频加载
        self.driver.touch(position)
        time.sleep(1)  # 等待视频加载

    def _switch_to_comment(self, fallback_position=(300, 930)):
        """切换到评论/讨论区
        Args:
            fallback_position: 如果找不到讨论按钮时的备用坐标，默认(300, 930)
        """
        try:
            # 尝试通过文本查找讨论按钮（Text类型）
            comment_element = self.driver.find_element(By.text("讨论"))
            comment_element.click()
        except:
            try:
                # 如果By不存在，尝试直接通过文本查找
                comment_element = self.driver.find_element_by_text("讨论")
                comment_element.click()
            except:
                # 如果都失败，使用driver执行坐标点击
                self.driver.touch(fallback_position)
        time.sleep(1)

    # ==================== 内部工具方法 ====================

    def _force_stop_app(self):
        """强制退出应用，避免后台进程残留"""
        try:
            # 尝试停止应用
            self.driver.stop_app(self.package_name)
            time.sleep(0.5)
        except:
            pass
        
        # 强制终止应用进程，确保完全退出
        try:
            command_kill = f'hdc shell \'kill -9 $(pidof {self.package_name}) 2>/dev/null || true\''
            subprocess.run(command_kill, shell=True)
            time.sleep(0.5)
        except:
            pass

    def _start_app_with_monitor_and_skip_ad(self):
        """公共方法：强制退出app、启动pmap监控、启动应用、跳过广告
        这个方法包含了所有用例都需要的公共启动流程
        """
        # 在启动监控前，强制退出app，避免后台进程残留
        Step('2.强制退出腾讯视频应用（避免后台进程残留）')
        self._force_stop_app()
        
        # 启动pmap监控，确保在应用启动时就开始采集
        Step('2.1.启动pmap内存监控')
        self._start_hidumper_monitor()
        
        Step('2.2.启动腾讯视频应用')
        self.driver.start_app(package_name=self.package_name)
        time.sleep(2.8)  # 等待应用启动和广告页加载
        
        Step('3.点击广告页右上角的跳过按钮')
        # 通过Text类型查找"跳过"按钮
        skip_found = False
        try:
            # 尝试通过文本查找跳过按钮（Text类型）
            skip_element = self.driver.find_element(By.text("跳过"))
            skip_element.click()
            skip_found = True
        except:
            try:
                # 如果By不存在，尝试直接通过文本查找
                skip_element = self.driver.find_element_by_text("跳过")
                skip_element.click()
                skip_found = True
            except:
                pass
        
        if not skip_found:
            # 如果找不到，点击固定位置(1139, 214)
            self.driver.touch((1139, 214))
        
        time.sleep(0.5)

    def _get_dump_file_path(self):
        """获取dump文件保存路径，如果文件已存在则添加数字后缀"""
        # 获取当前工程目录（testcases的父目录）
        current_dir = Path(__file__).parent.parent
        dump_dir = current_dir / "dump_output"
        dump_dir.mkdir(exist_ok=True)
        
        # 根据用例名称生成文件名
        case_name = self.__class__.__name__
        base_filename = f"{case_name}_memdump.log"
        file_path = dump_dir / base_filename
        
        # 如果文件已存在，添加数字后缀
        counter = 1
        while file_path.exists():
            name_part = f"{case_name}_memdump_{counter}.log"
            file_path = dump_dir / name_part
            counter += 1
        
        return str(file_path)
    
    def _get_profiler_file_path(self, suffix="htrace"):
        """获取profiler文件保存路径，如果文件已存在则添加数字后缀"""
        # 获取当前工程目录（testcases的父目录）
        current_dir = Path(__file__).parent.parent
        profiler_dir = current_dir / "hiperf_output"
        profiler_dir.mkdir(exist_ok=True)
        
        # 根据用例名称生成文件名
        case_name = self.__class__.__name__
        base_filename = f"{case_name}_profiler.{suffix}"
        file_path = profiler_dir / base_filename
        
        # 如果文件已存在，添加数字后缀
        counter = 1
        while file_path.exists():
            name_part = f"{case_name}_profiler_{counter}.{suffix}"
            file_path = profiler_dir / name_part
            counter += 1
        
        return str(file_path)
    
    def _wait_for_file(self, remote_path, timeout=60):
        """等待远程文件生成"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 检查文件是否存在
            check_cmd = f'hdc shell "test -f {remote_path} && echo exists || echo not_exists"'
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            if "exists" in result.stdout:
                return True
            time.sleep(1)
        return False

    def teardown(self):
        """公共teardown方法，子类可以重写或扩展"""
        # 停止pmap监控
        Step('7.1.停止pmap内存监控')
        self._stop_hidumper_monitor()
        
        # 只有当enable_memdump为True时才执行memdump相关操作
        if self.enable_memdump:
            Step('8.下载memdump.log文件到本地')
            # 获取保存路径
            local_file_path = self._get_dump_file_path()
            # 将memdump.log文件下载到本地
            command2 = f'hdc file recv /data/app/el2/100/base/{self.package_name}/files/memdump.log {local_file_path}'
            subprocess.run(command2, shell=True)
            time.sleep(1)

            Step('9.重置control.log')
            command3 = f'hdc shell \'echo "0" > /data/app/el2/100/base/{self.package_name}/files/control.log\''
            subprocess.run(command3, shell=True)
            time.sleep(0.5)
            
            # 将pmap采样数据追加到memdump文件末尾
            if self.hidumper_data:
                Step('9.1.将pmap采样数据追加到memdump文件')
                try:
                    with open(local_file_path, 'a', encoding='utf-8') as f:
                        f.write('\n')
                        f.write('=' * 80 + '\n')
                        f.write('Pmap采样数据 (anon:Kotlin内存信息，单位: kB)\n')
                        f.write('=' * 80 + '\n')
                        f.write('时间戳,虚拟内存(kB),物理内存(kB)\n')
                        for data_point in self.hidumper_data:
                            if len(data_point) == 3:
                                timestamp, virtual_mem, physical_mem = data_point
                                f.write(f'{timestamp},{virtual_mem},{physical_mem}\n')
                            elif len(data_point) == 2:
                                # 兼容旧格式（只有时间戳和大小）
                                timestamp, size = data_point
                                f.write(f'{timestamp},{size},0\n')
                        f.write('=' * 80 + '\n')
                    print(f"[Pmap Monitor] 已将 {len(self.hidumper_data)} 个数据点追加到 {local_file_path}")
                except Exception as e:
                    print(f"[Pmap Monitor] 追加数据到memdump文件失败: {e}")
        
        # 如果开启profiler，在关闭app前检查并导出htrace文件
        if self.enable_profiler:
            Step('10.等待hiprofiler_data.htrace文件生成')
            # 等待文件生成
            if self._wait_for_file("/data/local/tmp/hiprofiler_data.htrace"):
                Step('11.执行hidumper命令获取内存信息')
                # 执行hidumper命令，需要转义$符号
                command_hidumper = f'hdc shell "hidumper --mem \\$(pidof {self.package_name})"'
                result = subprocess.run(command_hidumper, shell=True, capture_output=True, text=True)
                Step('12.htrace文件生成后等待10秒')
                time.sleep(10)
                
                Step('13.导出hiprofiler_data.htrace文件到本地')
                # 获取保存路径
                local_profiler_path = self._get_profiler_file_path("htrace")
                # 导出htrace文件
                command_profiler = f'hdc file recv /data/local/tmp/hiprofiler_data.htrace {local_profiler_path}'
                subprocess.run(command_profiler, shell=True)
                time.sleep(1)
                
                # 保存hidumper输出到文件
                local_hidumper_path = self._get_profiler_file_path("hidumper.txt")
                with open(local_hidumper_path, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                    if result.stderr:
                        f.write("\n--- stderr ---\n")
                        f.write(result.stderr)
                time.sleep(0.5)
            else:
                Step('11.hiprofiler_data.htrace文件未生成，跳过导出')
        
        Step('14.关闭腾讯视频应用')
        self.driver.stop_app(self.package_name)
        time.sleep(0.5)
        
        Step('15.强制终止腾讯视频应用进程')
        # 使用kill命令强制终止应用进程，确保应用完全退出
        command4 = f'hdc shell \'kill -9 `pidof {self.package_name}`\''
        subprocess.run(command4, shell=True)
        time.sleep(0.5)

