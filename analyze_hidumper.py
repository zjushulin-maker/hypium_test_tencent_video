#!/usr/bin/env python
# coding: utf-8
"""
解析 hidumper.txt 文件，提取 PSS 数据，生成饼状图并保存为 Excel
"""

import re
import os
from pathlib import Path

try:
    import pandas as pd
    from openpyxl.chart import PieChart, Reference
    from openpyxl.chart.label import DataLabelList
    HAS_DEPENDENCIES = True
except ImportError as e:
    print(f"错误: 缺少必要的依赖包: {e}")
    print("请运行以下命令安装依赖:")
    print("  pip install pandas openpyxl")
    print("或者:")
    print("  pip install -r requirements_analyze.txt")
    HAS_DEPENDENCIES = False


def parse_hidumper_file(file_path):
    """
    解析 hidumper.txt 文件，提取 PSS 数据
    
    Returns:
        dict: {内存类型: PSS值(kB)}
        int: 总 PSS 值(kB)
    """
    pss_data = {}
    total_pss = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到数据开始的行（跳过表头和分隔线）
    # 分隔线特征是只包含 '-' 和空格，长度很长
    data_start = False
    for i, line in enumerate(lines):
        # 检查是否是真正的分隔线
        # 真正的分隔线只包含 '-' 和空格，长度超过 100
        stripped = line.strip()
        is_separator = (stripped.replace('-', '').replace(' ', '') == '' and 
                       len(stripped) > 100)
        
        if is_separator:
            if not data_start:
                # 找到第一个分隔线，数据在下一行开始
                data_start = True
                continue
            else:
                # 遇到第二个分隔线，说明数据部分结束
                break
        
        if data_start and line.strip():
            # 解析数据行
            # 格式示例: "            GL         226833              0              0..."
            # 使用正则表达式匹配：开头的空格+内存类型（可能包含多个单词）+空格+数字（PSS值）
            # 内存类型可能包含空格，所以需要找到第一个数字列
            parts = line.split()
            if len(parts) >= 2:
                # 找到第一个数字的位置（PSS Total列）
                pss_index = -1
                for j in range(len(parts)):
                    try:
                        int(parts[j])
                        pss_index = j
                        break
                    except ValueError:
                        continue
                
                if pss_index > 0:
                    # 内存类型是第一个数字之前的所有部分
                    mem_type = ' '.join(parts[:pss_index])
                    try:
                        pss_value = int(parts[pss_index])
                        
                        # 跳过 Total 行和空行
                        if mem_type.lower() != 'total' and mem_type.strip():
                            pss_data[mem_type] = pss_value
                    except (ValueError, IndexError):
                        continue
    
    # 从文件中查找 Total 行
    for line in lines:
        if 'Total' in line and len(line.split()) >= 2:
            parts = line.split()
            # 找到 Total 关键字的位置
            total_index = -1
            for i, part in enumerate(parts):
                if part.lower() == 'total':
                    total_index = i
                    break
            
            if total_index >= 0 and total_index + 1 < len(parts):
                try:
                    total_pss = int(parts[total_index + 1])
                    break
                except (ValueError, IndexError):
                    continue
    
    return pss_data, total_pss




def save_to_excel(pss_data, total_pss, output_excel_path):
    """
    将数据保存到 Excel，包含数据和可编辑的图表
    
    Args:
        pss_data: dict, {内存类型: PSS值(kB)}
        total_pss: int, 总 PSS 值(kB)
        output_excel_path: str, Excel 输出路径
    """
    # 过滤掉值为0的数据
    filtered_data = {k: v for k, v in pss_data.items() if v > 0}
    
    if not filtered_data:
        print("警告: 没有有效的数据可以绘制图表")
        return
    
    # 按值排序
    sorted_items = sorted(filtered_data.items(), key=lambda x: x[1], reverse=True)
    
    # 准备图表数据：包含所有项，如果超过15个则合并小的为"其他"
    if len(sorted_items) > 15:
        top15_items = sorted_items[:15]
        other_value = sum(v for _, v in sorted_items[15:])
        if other_value > 0:
            top15_items.append(("其他", other_value))
        chart_items = top15_items
    else:
        chart_items = sorted_items
    
    # 创建完整数据 DataFrame（用于数据表）
    data = {
        '内存类型': [],
        'PSS (kB)': [],
        'PSS (MB)': [],
        '占比 (%)': []
    }
    
    for mem_type, pss_value in sorted_items:
        percentage = (pss_value / total_pss * 100) if total_pss > 0 else 0
        data['内存类型'].append(mem_type)
        data['PSS (kB)'].append(pss_value)
        data['PSS (MB)'].append(round(pss_value / 1024, 2))
        data['占比 (%)'].append(round(percentage, 2))
    
    # 添加总计行
    data['内存类型'].append('总计')
    data['PSS (kB)'].append(total_pss)
    data['PSS (MB)'].append(round(total_pss / 1024, 2))
    data['占比 (%)'].append(100.0)
    
    df = pd.DataFrame(data)
    
    # 创建图表数据（用于饼图）：包含所有项
    chart_data = {
        '内存类型': [],
        'PSS (kB)': [],
        'PSS (MB)': [],
        '占比 (%)': []
    }
    
    for mem_type, pss_value in chart_items:
        percentage = (pss_value / total_pss * 100) if total_pss > 0 else 0
        chart_data['内存类型'].append(mem_type)
        chart_data['PSS (kB)'].append(pss_value)
        chart_data['PSS (MB)'].append(round(pss_value / 1024, 2))
        chart_data['占比 (%)'].append(round(percentage, 2))
    
    df_chart = pd.DataFrame(chart_data)
    
    # 保存到 Excel
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        # 写入完整数据
        df.to_excel(writer, sheet_name='PSS数据', index=False)
        
        # 写入图表数据（在另一个区域，用于创建图表）
        start_row = len(df) + 3
        df_chart.to_excel(writer, sheet_name='PSS数据', startrow=start_row, 
                         startcol=0, index=False, header=False)
        
        # 获取 workbook 和 worksheet
        workbook = writer.book
        worksheet = writer.sheets['PSS数据']
        
        # 调整列宽
        worksheet.column_dimensions['A'].width = 30
        worksheet.column_dimensions['B'].width = 15
        worksheet.column_dimensions['C'].width = 15
        worksheet.column_dimensions['D'].width = 15
        
        # 创建饼状图
        pie = PieChart()
        pie.title = f"内存 PSS 分布图 (总 PSS: {total_pss/1024:.2f} MB)"
        
        # 设置数据范围（图表数据区域）
        # 标签列（A列）
        labels = Reference(worksheet, min_col=1, min_row=start_row+1, 
                          max_row=start_row+len(df_chart))
        # 数值列（B列，PSS值）
        data = Reference(worksheet, min_col=2, min_row=start_row+1, 
                        max_row=start_row+len(df_chart))
        
        pie.add_data(data, titles_from_data=False)
        pie.set_categories(labels)
        
        # 去掉默认的系列名称（"系列1"）
        if len(pie.series) > 0:
            pie.series[0].name = ""
        
        # 设置数据标签：只对占比大于5%的显示标签
        pie.dataLabels = DataLabelList()
        pie.dataLabels.showPercent = True
        pie.dataLabels.showVal = True
        pie.dataLabels.showCatName = True
        pie.dataLabels.position = 'bestFit'
        
        # 使用 DataPoint 控制哪些数据点显示标签（占比>5%）
        from openpyxl.chart.series import DataPoint
        pie.series[0].dPt = []
        
        for i, row in df_chart.iterrows():
            percentage = row['占比 (%)']
            dp = DataPoint(idx=i)
            if percentage > 5:
                # 占比大于5%的显示标签
                from openpyxl.chart.label import DataLabelList as DPDataLabelList
                dp.dLbls = DPDataLabelList()
                dp.dLbls.showCatName = True
                dp.dLbls.showPercent = True
                dp.dLbls.showVal = True
                dp.dLbls.position = 'bestFit'
            else:
                # 占比小于等于5%的不显示标签
                from openpyxl.chart.label import DataLabelList as DPDataLabelList
                dp.dLbls = DPDataLabelList()
                dp.dLbls.showCatName = False
                dp.dLbls.showPercent = False
                dp.dLbls.showVal = False
            pie.series[0].dPt.append(dp)
        
        # 设置图表大小和位置
        pie.width = 15
        pie.height = 10
        
        # 将图表添加到工作表（放在数据右侧）
        worksheet.add_chart(pie, "F2")
    
    print(f"Excel 文件已保存: {output_excel_path}")


def process_hidumper_file(hidumper_file_path):
    """
    处理单个 hidumper.txt 文件
    
    Args:
        hidumper_file_path: str, hidumper.txt 文件路径
    """
    print(f"正在处理: {hidumper_file_path}")
    
    # 解析文件
    pss_data, total_pss = parse_hidumper_file(hidumper_file_path)
    
    if not pss_data:
        print(f"警告: 无法从 {hidumper_file_path} 中提取数据")
        return
    
    print(f"总 PSS: {total_pss} kB ({total_pss/1024:.2f} MB)")
    print(f"找到 {len(pss_data)} 个内存类型")
    
    # 生成输出路径
    file_path = Path(hidumper_file_path)
    base_name = file_path.stem  # 不包含扩展名
    output_dir = file_path.parent
    
    # 保存到 Excel（包含可编辑的图表）
    excel_path = output_dir / f"{base_name}_analysis.xlsx"
    save_to_excel(pss_data, total_pss, str(excel_path))
    
    print(f"分析完成: {excel_path}\n")


def main():
    """主函数"""
    if not HAS_DEPENDENCIES:
        return
    
    # 获取 hiperf_output 目录
    current_dir = Path(__file__).parent
    hiperf_dir = current_dir / "hiperf_output"
    
    if not hiperf_dir.exists():
        print(f"错误: 目录不存在 {hiperf_dir}")
        return
    
    # 查找所有 hidumper.txt 文件
    hidumper_files = list(hiperf_dir.glob("*hidumper.txt"))
    
    if not hidumper_files:
        print(f"未找到 hidumper.txt 文件在 {hiperf_dir}")
        return
    
    print(f"找到 {len(hidumper_files)} 个 hidumper.txt 文件\n")
    
    # 处理每个文件
    for hidumper_file in hidumper_files:
        try:
            process_hidumper_file(str(hidumper_file))
        except Exception as e:
            print(f"处理 {hidumper_file} 时出错: {e}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()

