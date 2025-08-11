import gradio as gr
import os
import shutil
from datetime import datetime
import zipfile
import logging

# 创建文件夹
INPUT_DIR = "input_videos"
OUTPUT_DIR = "output_videos"
DOWNLOAD_DIR = "downloads"  # 下载目录
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)  # 确保下载目录存在

# 初始化文件状态跟踪变量
last_input_files = []
last_output_files = []

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_info(message):
    """记录INFO级别日志"""
    logging.info(message)

def log_error(message):
    """记录ERROR级别日志"""
    logging.error(message)

def list_files(directory):
    """列出目录中的所有视频文件"""
    files = []
    for f in os.listdir(directory):
        if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            path = os.path.join(directory, f)
            size = f"{os.path.getsize(path) / 1024 / 1024:.2f} MB"
            mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M')
            # 修改：返回列表而不是元组
            files.append([False, f, path, size, mtime])  # 使用方括号创建列表
    log_info(f"列出目录 {directory} 中的文件，找到 {len(files)} 个视频文件")
    return files


# 修改刷新函数 - 仅当文件实际变化时刷新
def refresh_files_only():
    """仅当文件变化时刷新文件列表，保留当前选中状态"""
    global last_input_files, last_output_files
    
    # 获取当前文件列表
    current_input = list_files(INPUT_DIR)
    current_output = list_files(OUTPUT_DIR)
    
    # 检查文件是否有变化
    input_changed = current_input != last_input_files
    output_changed = current_output != last_output_files
    
    # 更新最后已知状态
    if input_changed:
        last_input_files = current_input
        log_info(f"检测到input目录文件变化，已更新文件列表，当前文件数: {len(current_input)}")
    if output_changed:
        last_output_files = current_output
        log_info(f"检测到output目录文件变化，已更新文件列表，当前文件数: {len(current_output)}")
    
    # 只有变化时才返回新列表
    if input_changed or output_changed:
        return current_input, current_output
    else:
        # 没有变化时返回gr.update()以保持当前状态
        log_info("文件未发生变化，保持当前状态")
        return gr.update(), gr.update()


# 完整刷新函数 - 用于上传/删除等操作
def full_refresh():
    """完全刷新文件列表并清空选中状态"""
    global last_input_files, last_output_files
    
    input_list = list_files(INPUT_DIR)
    output_list = list_files(OUTPUT_DIR)
    
    # 更新最后已知状态
    last_input_files = input_list
    last_output_files = output_list
    
    log_info(f"执行完整刷新，input文件数: {len(input_list)}, output文件数: {len(output_list)}")
    return input_list, output_list, [], []


def upload_file(file):
    """上传文件到input目录"""
    if file:
        filename = os.path.basename(file.name)
        dest = os.path.join(INPUT_DIR, filename)
        shutil.copy(file.name, dest)
        log_info(f"上传文件: {filename} 到 {INPUT_DIR} 目录")
    else:
        log_info("未选择文件进行上传")
    return full_refresh()


def delete_files(file_paths):
    """批量删除文件"""
    if not file_paths:
        log_info("删除请求中未选择文件")
        return full_refresh()
        
    deleted_count = 0
    for path in file_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
                log_info(f"删除文件: {path}")
                deleted_count += 1
            except Exception as e:
                log_error(f"删除文件失败: {path}, 错误: {str(e)}")
        else:
            log_error(f"尝试删除不存在的文件: {path}")
    
    log_info(f"批量删除完成，成功删除 {deleted_count} 个文件")
    return full_refresh()


def download_files(file_paths):
    """批量下载文件 - 创建ZIP压缩包"""
    if not file_paths:
        log_info("下载请求中未选择文件")
        return None, "📥 请先选择要下载的文件！"  # 添加错误提示
    
    # 确定来源文件夹名称 (input/output)
    source_dir = "input" if file_paths and file_paths[0].startswith(INPUT_DIR) else "output"
    
    # 获取文件名（不带扩展名）
    if len(file_paths) == 1:
        base_name = os.path.splitext(os.path.basename(file_paths[0]))[0]
        zip_name = f"{source_dir}_{base_name}.zip"
    else:
        zip_name = f"{source_dir}_多个文件.zip"
    
    zip_path = os.path.join(DOWNLOAD_DIR, zip_name)
    
    try:
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for path in file_paths:
                if os.path.exists(path):
                    zipf.write(path, os.path.basename(path))
                    log_info(f"添加文件到压缩包: {path}")
                else:
                    log_error(f"尝试添加不存在的文件到压缩包: {path}")

        log_info(f"下载文件准备完成: {zip_path}")
        return zip_path, "📥 下载文件已准备好！"  # 添加成功提示
    except Exception as e:
        log_error(f"创建下载文件失败: {str(e)}")
        return None, "📥 下载文件准备失败！"


def preview_file(file_path):
    """预览单个视频文件"""
    if file_path and os.path.exists(file_path):
        log_info(f"预览文件: {file_path}")
        return file_path
    else:
        log_info(f"尝试预览不存在的文件: {file_path}")
        return None


def list_downloads():
    """列出下载目录中的所有文件"""
    downloads = [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) 
                 if os.path.isfile(os.path.join(DOWNLOAD_DIR, f))]
    log_info(f"列出下载目录文件，当前有 {len(downloads)} 个下载文件")
    return downloads


def clear_downloads():
    """清除下载目录中的所有文件"""
    cleared_count = 0
    for f in os.listdir(DOWNLOAD_DIR):
        file_path = os.path.join(DOWNLOAD_DIR, f)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
                log_info(f"清除下载文件: {file_path}")
                cleared_count += 1
        except Exception as e:
            log_error(f"删除下载文件失败: {file_path} - {e}")
    
    log_info(f"下载目录清理完成，共清除 {cleared_count} 个文件")
    return "📥 下载文件已清除！", list_downloads()


# 文件选择处理函数
def update_selections(input_df, output_df, input_selected, output_selected):
    """更新选中的文件并返回完整表格数据"""
    try:
        # 处理Input选择
        input_paths = [row[2] for row in input_df] if input_df else []
        output_paths = [row[2] for row in output_df] if output_df else []

        # 直接使用表格中的选中状态
        new_input_selected = [path for i, path in enumerate(input_paths) 
                            if i < len(input_df) and input_df[i][0]]
      
        new_output_selected = [path for i, path in enumerate(output_paths) 
                             if i < len(output_df) and output_df[i][0]]

        # 更新计数显示
        input_count = len(new_input_selected)
        output_count = len(new_output_selected)
      
        # 更新表格显示状态
        updated_input_df = []
        for i, row in enumerate(input_df):
            updated_row = list(row)
            if i < len(input_paths):
                updated_row[0] = input_paths[i] in new_input_selected
            updated_input_df.append(updated_row)
      
        updated_output_df = []
        for i, row in enumerate(output_df):
            updated_row = list(row)
            if i < len(output_paths):
                updated_row[0] = output_paths[i] in new_output_selected
            updated_output_df.append(updated_row)
      
        log_info(f"更新选择状态 - Input选中: {input_count}, Output选中: {output_count}")
        return (
            new_input_selected,  # 更新选中文件路径
            new_output_selected,  # 更新选中文件路径
            str(input_count),
            "\n".join([f"• {os.path.basename(p)}" for p in new_input_selected]) or "暂无选中文件",
            str(output_count),
            "\n".join([f"• {os.path.basename(p)}" for p in new_output_selected]) or "暂无选中文件",
            updated_input_df,  # 返回带有正确选中状态的表格数据
            updated_output_df   # 返回带有正确选中状态的表格数据
        )
    except Exception as e:
        log_error(f"更新选择时出错: {e}")
        return input_selected, output_selected, "0", "暂无选中文件", "0", "暂无选中文件", input_df, output_df


# 创建安全更新函数，只返回选择状态
def safe_update_selections(input_df, output_df, input_selected, output_selected):
    """安全地更新选择状态（不在UI上刷新文件列表）"""
    # 只返回选择相关的状态
    result = update_selections(input_df, output_df, input_selected, output_selected)
    # 返回：selected_input, selected_output, input_count, input_display, output_count, output_display
    log_info(f"安全更新选择状态 - Input选中: {len(result[0])}, Output选中: {len(result[1])}")
    return result[0:6]


def select_all_files(df, is_input=True):
    """全选当前文件夹的文件"""
    folder_name = "Input" if is_input else "Output"
    log_info(f"执行全选操作 - {folder_name}文件夹")
    
    if not df:
        log_info(f"{folder_name}文件夹为空，无可选文件")
        return [], "0", "暂无选中文件", df
    
    # 获取所有文件路径
    all_paths = [row[2] for row in df]
    
    # 更新表格数据，将所有选择列设为True
    updated_df = []
    for row in df:
        new_row = list(row)
        new_row[0] = True  # 选中状态
        updated_df.append(new_row)
    
    # 更新选中状态
    count = len(all_paths)
    display = "\n".join([f"• {os.path.basename(p)}" for p in all_paths]) or "暂无选中文件"
    
    log_info(f"全选完成 - {folder_name}文件夹，选中文件数: {count}")
    return all_paths, str(count), display, updated_df


def clear_selection_files(df, is_input=True):
    """清空当前文件夹的文件选择"""
    folder_name = "Input" if is_input else "Output"
    log_info(f"执行清空选择操作 - {folder_name}文件夹")
    
    if not df:
        log_info(f"{folder_name}文件夹为空，无文件可取消选择")
        return [], "0", "暂无选中文件", df
    
    # 更新表格数据，将所有选择列设为False
    updated_df = []
    for row in df:
        new_row = list(row)
        new_row[0] = False  # 取消选中状态
        updated_df.append(new_row)
    
    # 更新选中状态
    count = 0
    display = "暂无选中文件"
    
    log_info(f"清空选择完成 - {folder_name}文件夹")
    return [], str(count), display, updated_df


def update_preview_selector(input_selected, output_selected):
    """更新预览选择器的选项"""
    # 合并输入和输出文件夹的选中文件
    all_selected_files = []
    
    # 添加Input文件夹选中的文件
    if input_selected:
        for file_path in input_selected:
            file_name = os.path.basename(file_path)
            all_selected_files.append((f"[Input] {file_name}", file_path))
    
    # 添加Output文件夹选中的文件
    if output_selected:
        for file_path in output_selected:
            file_name = os.path.basename(file_path)
            all_selected_files.append((f"[Output] {file_name}", file_path))
    
    log_info(f"更新预览选择器选项，共有 {len(all_selected_files)} 个选中文件")
    # 返回选项列表和默认选中值（第一个文件）
    if all_selected_files:
        return gr.update(choices=all_selected_files, value=all_selected_files[0][1])
    else:
        return gr.update(choices=[], value=None)


# 创建Gradio界面
with gr.Blocks(title="视频文件管理预览系统") as demo:
    gr.Markdown("## 🎥 视频文件管理预览系统")
    gr.Markdown("上传视频到input目录，处理后的视频保存到output目录")

    # 存储选中的文件路径
    selected_input_files = gr.State([])
    selected_output_files = gr.State([])

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 📤 Input文件夹")
            # 初始化时使用完整刷新函数获取文件列表
            initial_input, initial_output, _, _ = full_refresh()
            
            input_files = gr.DataFrame(
                headers=["选择", "文件名", "路径", "大小", "修改时间"],
                datatype=["bool", "str", "str", "str", "str"],
                interactive=True,
                type="array",
                value=initial_input  # 设置初始值
            )

            with gr.Row():
                # 移除全选复选框，改为全选按钮
                select_all_input_btn = gr.Button("✅ 全选", size="sm")
                clear_selection_input_btn = gr.Button("⭕ 清空选择", size="sm")
                refresh_input_btn = gr.Button("🔄 刷新", size="sm")
                upload_btn = gr.UploadButton("⬆️ 上传视频", file_types=["video"], size="sm")
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("**已选中文件:**")
                    input_selected_count = gr.Textbox("0", label="数量")
                    input_selected_display = gr.Textbox("暂无选中文件", label="文件列表", lines=4, interactive=False)

            with gr.Row():
                download_selected_input = gr.Button("📥 下载选中文件", size="sm")
                delete_selected_input = gr.Button("🗑️ 删除选中文件", variant="stop", size="sm")
                clear_input_btn = gr.Button("🧹 清空文件夹", variant="stop", size="sm")
                download_all_input = gr.Button("📦 下载全部", size="sm")

        with gr.Column():
            gr.Markdown("### 📥 Output文件夹")
            output_files = gr.DataFrame(
                headers=["选择", "文件名", "路径", "大小", "修改时间"],
                datatype=["bool", "str", "str", "str", "str"],
                interactive=True,
                type="array",
                value=initial_output  # 设置初始值
            )

            with gr.Row():
                # 移除全选复选框，改为全选按钮
                select_all_output_btn = gr.Button("✅ 全选", size="sm")
                clear_selection_output_btn = gr.Button("⭕ 清空选择", size="sm")
                refresh_output_btn = gr.Button("🔄 刷新", size="sm")

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("**已选中文件:**")
                    output_selected_count = gr.Textbox("0", label="数量")
                    output_selected_display = gr.Textbox("暂无选中文件", label="文件列表", lines=4, interactive=False)

            with gr.Row():
                download_selected_output = gr.Button("📥 下载选中文件", size="sm")
                delete_selected_output = gr.Button("🗑️ 删除选中文件", variant="stop", size="sm")
                clear_output_btn = gr.Button("🧹 清空文件夹", variant="stop", size="sm")
                download_all_output = gr.Button("📦 下载全部", size="sm")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📺 视频预览")
            # 添加下拉框用于选择预览视频
            preview_selector = gr.Dropdown(choices=[], label="选择预览视频", interactive=True)
            video_preview = gr.Video(height=300, interactive=False)

            with gr.Row():
                preview_btn = gr.Button("👁️ 预览选中视频")
                clear_preview_btn = gr.Button("🧹 清除预览", size="sm")
            
            # 添加预览下拉框到状态管理
            selected_preview_file = gr.State(None)
            # 下载组件
            download_comp = gr.File(label="下载文件", value=list_downloads())  # 初始化时列出已有下载
            
            # 添加清除下载按钮
            with gr.Row():
                clear_downloads_btn = gr.Button("🗑️ 清除所有下载文件", size="sm", variant="stop")

    # 状态区域
    status = gr.Textbox(label="操作状态", interactive=False)

    # 删除之前的初始化调用（已移到组件创建时）
    # initial_input, initial_output, _, _ = full_refresh()


    # 绑定事件 - 只选择状态更新
    input_files.change(
        fn=safe_update_selections,
        inputs=[input_files, output_files, selected_input_files, selected_output_files],
        outputs=[
            selected_input_files,
            selected_output_files,
            input_selected_count,
            input_selected_display,
            output_selected_count,
            output_selected_display
        ]
    )

    output_files.change(
        fn=safe_update_selections,
        inputs=[input_files, output_files, selected_input_files, selected_output_files],
        outputs=[
            selected_input_files,
            selected_output_files,
            input_selected_count,
            input_selected_display,
            output_selected_count,
            output_selected_display
        ]
    )
    
    # 更新预览选择器选项当选择状态变化时
    selected_input_files.change(
        fn=update_preview_selector,
        inputs=[selected_input_files, selected_output_files],
        outputs=preview_selector
    )
    
    selected_output_files.change(
        fn=update_preview_selector,
        inputs=[selected_input_files, selected_output_files],
        outputs=preview_selector
    )
    
    # 当预览选择器变更时自动预览选中的视频
    preview_selector.change(
        fn=preview_file,
        inputs=preview_selector,
        outputs=video_preview
    )
    
    # 刷新功能 - 仅刷新文件列表
    refresh_input_btn.click(
        fn=lambda: [log_info("点击刷新Input文件夹"), refresh_files_only()][1],
        outputs=[input_files, output_files]
    )

    refresh_output_btn.click(
        fn=lambda: [log_info("点击刷新Output文件夹"), refresh_files_only()][1],
        outputs=[input_files, output_files]
    )

    # 上传功能 - 完全刷新
    upload_btn.upload(
        fn=upload_file,
        inputs=upload_btn,
        outputs=[input_files, output_files, selected_input_files, selected_output_files]
    )

    # 预览功能 - 支持从下拉框选择或默认选择第一个
    preview_btn.click(
        fn=lambda input_selected, output_selected, selected_preview: preview_file(
            selected_preview if selected_preview else (
                input_selected[0] if input_selected else (
                    output_selected[0] if output_selected else None
                )
            )
        ),
        inputs=[selected_input_files, selected_output_files, preview_selector],
        outputs=video_preview
    )

    clear_preview_btn.click(
        fn=lambda: [log_info("清除视频预览"), None], 
        outputs=video_preview
    )

    # 删除功能 - 选中文件
    delete_selected_input.click(
        fn=delete_files,
        inputs=selected_input_files,
        outputs=[input_files, output_files, selected_input_files, selected_output_files]
    )

    delete_selected_output.click(
        fn=delete_files,
        inputs=selected_output_files,
        outputs=[input_files, output_files, selected_input_files, selected_output_files]
    )

    # 下载功能 - 选中文件
    def download_and_refresh(file_paths):
        zip_path, msg = download_files(file_paths)
        return zip_path, msg, list_downloads()
    
    download_selected_input.click(
        fn=download_and_refresh,
        inputs=selected_input_files,
        outputs=[download_comp, status, download_comp]  # 更新两次以刷新列表
    )

    download_selected_output.click(
        fn=download_and_refresh,
        inputs=selected_output_files,
        outputs=[download_comp, status, download_comp]  # 更新两次以刷新列表
    )

    # 下载全部文件
    download_all_input.click(
        fn=lambda: download_and_refresh([os.path.join(INPUT_DIR, f) for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))]),
        outputs=[download_comp, status, download_comp]
    )

    download_all_output.click(
        fn=lambda: download_and_refresh([os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))]),
        outputs=[download_comp, status, download_comp]
    )

    # 清空文件夹
    clear_input_btn.click(
        fn=lambda: [log_info("清空Input文件夹"), delete_files([os.path.join(INPUT_DIR, f) for f in os.listdir(INPUT_DIR)])][1:],
        outputs=[input_files, output_files, selected_input_files, selected_output_files]
    )

    clear_output_btn.click(
        fn=lambda: [log_info("清空Output文件夹"), delete_files([os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR)])][1:],
        outputs=[input_files, output_files, selected_input_files, selected_output_files]
    )
    
    # 绑定清除下载事件
    clear_downloads_btn.click(
        fn=clear_downloads,
        outputs=[status, download_comp]  # 更新状态和下载组件
    )
    
    # 全选按钮功能 - Input文件夹
    select_all_input_btn.click(
        fn=lambda df: select_all_files(df, True),
        inputs=input_files,
        outputs=[
            selected_input_files,
            input_selected_count,
            input_selected_display,
            input_files
        ]
    )

    # 全选按钮功能 - Output文件夹
    select_all_output_btn.click(
        fn=lambda df: select_all_files(df, False),
        inputs=output_files,
        outputs=[
            selected_output_files,
            output_selected_count,
            output_selected_display,
            output_files
        ]
    )
    
    # 清空选择按钮功能 - Input文件夹
    clear_selection_input_btn.click(
        fn=lambda df: clear_selection_files(df, True),
        inputs=input_files,
        outputs=[
            selected_input_files,
            input_selected_count,
            input_selected_display,
            input_files
        ]
    )

    # 清空选择按钮功能 - Output文件夹
    clear_selection_output_btn.click(
        fn=lambda df: clear_selection_files(df, False),
        inputs=output_files,
        outputs=[
            selected_output_files,
            output_selected_count,
            output_selected_display,
            output_files
        ]
    )

# 启动应用
if __name__ == "__main__":
    log_info("启动视频文件管理预览系统")
    demo.launch(
        server_port=7860,
        share=False,
        inbrowser=True
    )
    log_info("视频文件管理预览系统已关闭")