from xdevice.__main__ import main_process
from xdevice import SuiteReporter
from pathlib import Path
import argparse
import datetime
import subprocess
import time

# ANSI 颜色
_R = "\033[1;31m"   # 红色（崩溃/失败）
_Y = "\033[1;33m"   # 黄色（提示）
_C = "\033[1;36m"   # 青色（进度）
_W = "\033[1;37m"   # 白色（标题）
_X = "\033[0m"      # 重置

# 设备 faultlog 目录
FAULT_DIR = "/data/log/faultlog/faultlogger"
# 只关注与目标应用相关的 fault 类型
FAULT_KEYWORDS = ("cppcrash", "appfreeze", "jscrash", "sysfreeze")
PACKAGE_NAME   = "com.tencent.videohm"


def parse_args():
    parser = argparse.ArgumentParser(
        description="腾讯视频压测脚本",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-r", "--repeat",
        type=int,
        default=100,
        metavar="N",
        help="压测轮数，0 = 无限循环直到 Ctrl+C（默认：100）",
    )
    parser.add_argument(
        "-sn", "--device-sn",
        type=str,
        default="",
        metavar="SN",
        help="指定设备 SN，多台用 ';' 分隔（默认：使用当前连接的设备）\n"
             "示例: -sn ABCD1234\n"
             "示例: -sn ABCD1234;EFGH5678",
    )
    parser.add_argument(
        "-rp", "--report-path",
        type=str,
        default="reports",
        metavar="PATH",
        help="报告输出目录（默认：./reports）",
    )
    parser.add_argument(
        "-fp", "--fault-path",
        type=str,
        default="faultlogs",
        metavar="PATH",
        help="faultlog 本地保存目录（默认：./faultlogs）",
    )
    parser.add_argument(
        "-c", "--cases",
        type=str,
        nargs="+",
        default=None,
        metavar="CASE",
        help="指定要运行的用例名，多个用空格分隔（默认：运行全部用例）\n"
             "示例: -c TencentVideoButton\n"
             "示例: -c TencentVideoButton TencentVideoHome",
    )
    return parser.parse_args()


def get_all_testcases(testcases_dir="testcases"):
    """扫描 testcases 目录，以存在对应 .json 配置的文件为可运行用例"""
    base = Path(testcases_dir)
    return sorted(p.stem for p in base.glob("*.json"))


# ── faultlog 收集 ────────────────────────────────────────

def _hdc(device_sn, subcmd):
    """执行 hdc 命令，返回 stdout 字符串，失败返回空字符串"""
    sn_arg = f"-t {device_sn} " if device_sn else ""
    result = subprocess.run(
        f"hdc {sn_arg}{subcmd}",
        shell=True, capture_output=True, text=True,
    )
    return result.stdout if result.returncode == 0 else ""


def snapshot_fault_logs(device_sn):
    """返回设备上当前与目标应用相关的 faultlog 文件名集合"""
    out = _hdc(device_sn, f"shell ls {FAULT_DIR}/")
    files = set()
    for line in out.splitlines():
        name = line.strip()
        if name and PACKAGE_NAME in name and any(k in name for k in FAULT_KEYWORDS):
            files.add(name)
    return files


def collect_new_fault_logs(device_sn, known_files, round_num, fault_save_dir):
    """
    对比 known_files，拉取本轮新增的 faultlog 到本地。
    返回已保存的本地路径列表（空列表表示本轮无新问题）。
    """
    current = snapshot_fault_logs(device_sn)
    new_files = sorted(current - known_files)
    if not new_files:
        return []

    save_dir = Path(fault_save_dir) / f"round_{round_num:04d}"
    save_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for fname in new_files:
        remote = f"{FAULT_DIR}/{fname}"
        local  = save_dir / fname
        _hdc(device_sn, f"file recv {remote} {local}")
        if local.exists():
            saved.append(str(local))

    return saved


def _print_fault_banner(round_num, saved_paths):
    """打印醒目的 faultlog 告警"""
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "★" * 62
    print(f"\n{_R}{sep}")
    print(f"  ⚠  设备异常告警（新增 faultlog）")
    print(f"  时间：{ts}")
    print(f"  轮次：第 {round_num} 轮")
    print(f"  共发现 {len(saved_paths)} 个新问题文件：")
    for p in saved_paths:
        print(f"    → {p}")
    print(f"{sep}{_X}\n")


# ── uitest daemon 管理 ───────────────────────────────────

def _setup_uitest(device_sn):
    """
    重启 uitest daemon 并预建端口转发，解决两类 Connection Refused 问题：
      场景A：daemon 冷启动后框架立即连接，socket 未就绪（竞态条件）
      场景B：daemon 已在运行，但上次测试结束后端口转发规则已失效
    """
    sn_arg = f"-t {device_sn} " if device_sn else ""

    # 1. 终止旧 daemon，确保干净启动
    _hdc(device_sn, "shell pkill -f 'uitest start-daemon'")
    time.sleep(0.5)

    # 2. 清理残留端口转发规则（失败无妨）
    _hdc(device_sn, "fport rm tcp:9969")

    # 3. 后台启动新 daemon
    subprocess.Popen(
        f"hdc {sn_arg}shell /system/bin/uitest start-daemon singleness",
        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    # 4. 等待 unix socket 就绪（最多 10 秒，每 0.5 秒轮询一次）
    for _ in range(20):
        time.sleep(0.5)
        if "uitest_socket" in _hdc(device_sn, "shell cat /proc/net/unix"):
            break

    # 5. 建立 TCP 端口转发
    _hdc(device_sn, "fport tcp:9969 localabstract:uitest_socket")
    time.sleep(0.3)


# ── 用例运行 ─────────────────────────────────────────────

def _print_failure_banner(case_name, round_num, reason):
    """打印用例执行失败告警"""
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "!" * 62
    print(f"\n{_R}{sep}")
    print(f"  ✖  用例失败告警")
    print(f"  时间：{ts}")
    print(f"  轮次：第 {round_num} 轮")
    print(f"  用例：{case_name}")
    if reason:
        if isinstance(reason, list):
            for item in reason:
                print(f"  详情：{item}")
        else:
            print(f"  详情：{reason}")
    print(f"{sep}{_X}\n")


def run_one_case(case_name, round_num, report_path, device_sn):
    """运行单个用例，失败时打印告警并返回 False，不中断整体压测"""
    # 每次运行前重建 uitest daemon + 端口转发，解决 Connection Refused
    _setup_uitest(device_sn)

    # 每个用例使用独立子目录，避免 xdevice "report path must be empty" 报错
    unique_rp = f"{report_path}/r{round_num:04d}_{case_name}"
    sn_arg = f" -sn {device_sn}" if device_sn else ""
    cmd = f"run -l {case_name} -rp {unique_rp}{sn_arg} -ta agent_mode:bin"
    try:
        main_process(cmd)
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        _print_failure_banner(case_name, round_num, f"框架异常: {type(exc).__name__}: {exc}")
        return False

    failed = SuiteReporter.get_failed_case_list()
    if failed:
        _print_failure_banner(case_name, round_num, [str(f) for f in failed])
        return False

    return True


# ── 主流程 ───────────────────────────────────────────────

if __name__ == "__main__":
    args = parse_args()
    repeat        = args.repeat
    device_sn     = args.device_sn
    report_path   = args.report_path
    fault_save_dir = args.fault_path

    all_cases = get_all_testcases()
    if args.cases:
        unknown = [c for c in args.cases if c not in all_cases]
        if unknown:
            print(f"{_R}未知用例：{unknown}")
            print(f"可用用例：{all_cases}{_X}")
            raise SystemExit(1)
        cases = args.cases
    else:
        cases = all_cases

    print(f"{_C}发现用例（共 {len(cases)} 个）：{cases}")
    print(f"压测轮数：{'∞' if repeat == 0 else repeat}")
    print(f"设备 SN ：{device_sn or '（使用当前连接设备）'}")
    print(f"报告目录：{report_path}")
    print(f"故障日志：{fault_save_dir}{_X}")

    loop = 0
    try:
        while repeat == 0 or loop < repeat:
            loop += 1
            print(f"\n{_C}{'─' * 55}")
            print(f"  第 {loop:>4} 轮 / {'∞' if repeat == 0 else repeat}")
            print(f"{'─' * 55}{_X}")

            # 本轮开始前记录设备上已有的 faultlog 快照
            known_faults = snapshot_fault_logs(device_sn)

            for case in cases:
                ok = run_one_case(case, loop, report_path, device_sn)
                if not ok:
                    print(f"  {_Y}⏭  {case} 失败，跳过，继续下一用例{_X}")

            # 本轮结束后收集新增 faultlog
            new_logs = collect_new_fault_logs(device_sn, known_faults, loop, fault_save_dir)
            if new_logs:
                _print_fault_banner(loop, new_logs)

    except KeyboardInterrupt:
        print(f"\n{_Y}压测已手动停止，共完成 {loop} 轮{_X}")

    print(f"\n{_W}{'═' * 55}")
    print(f"  压测完成 · 共 {loop} 轮")
    print(f"{'═' * 55}{_X}\n")
