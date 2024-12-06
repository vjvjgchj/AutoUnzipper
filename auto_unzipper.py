import os
import logging
import yaml
import inotify.adapters
import zipfile
import tarfile
import rarfile
import requests
from pytablewriter import MarkdownTableWriter


class AutoUnzipper:
    def __init__(self, config_path='config.yaml'):
        """
        初始化自动解压器

        :param config_path: 配置文件路径
        """
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

        # 加载配置
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.error(f"配置文件 {config_path} 未找到")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"配置文件解析错误: {e}")
            raise

        # 支持的压缩文件扩展名
        self.supported_extensions = {
            '.zip': self._unzip_file,
            '.tar': self._untar_file,
            '.tar.gz': self._untar_file,
            '.tgz': self._untar_file,
            '.rar': self._unrar_file
        }

    def _is_extractable(self, filename):
        """
        检查文件是否可解压，排除包含 noextract 的文件

        :param filename: 文件名
        :return: 是否可解压
        """
        return (
                any(filename.lower().endswith(ext) for ext in self.supported_extensions)
                and 'noextract' not in filename.lower()
        )

    def _create_extract_folder(self, file_path):
        """
        创建与压缩文件同名的文件夹，位于压缩文件上层目录

        :param file_path: 压缩文件路径
        :return: 目标解压目录
        """
        parent_dir = os.path.dirname(file_path)
        upper_dir = os.path.dirname(parent_dir)  # 上层目录
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        target_dir = os.path.join(upper_dir, base_filename)

        counter = 1
        while os.path.exists(target_dir):
            target_dir = os.path.join(upper_dir, f"{base_filename}_{counter}")
            counter += 1

        os.makedirs(target_dir)
        return target_dir

    def _unzip_file(self, file_path, target_dir):
        """
        解压ZIP文件

        :param file_path: 压缩文件路径
        :param target_dir: 目标解压目录
        """
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            self.logger.info(f"成功解压 {file_path}")
        except Exception as e:
            self.logger.error(f"解压 {file_path} 失败: {e}")

    def _untar_file(self, file_path, target_dir):
        """
        解压TAR文件

        :param file_path: 压缩文件路径
        :param target_dir: 目标解压目录
        """
        try:
            with tarfile.open(file_path, 'r:*') as tar_ref:
                tar_ref.extractall(target_dir)
            self.logger.info(f"成功解压 {file_path}")
        except Exception as e:
            self.logger.error(f"解压 {file_path} 失败: {e}")

    def _unrar_file(self, file_path, target_dir):
        """
        解压RAR文件

        :param file_path: 压缩文件路径
        :param target_dir: 目标解压目录
        """
        try:
            with rarfile.RarFile(file_path) as rar_ref:
                rar_ref.extractall(target_dir)
            self.logger.info(f"成功解压 {file_path}")
        except Exception as e:
            self.logger.error(f"解压 {file_path} 失败: {e}")

    def process_file(self, file_path, extract_mode, product_line, webhook_url):
        """
        处理文件解压

        :param file_path: 要处理的文件路径
        :param extract_mode: 解压模式 (direct 或 nested)
        :param product_line: 产品线名称
        :param webhook_url: 钉钉 Webhook URL
        """
        if not self._is_extractable(file_path):
            return

        file_name = os.path.basename(file_path)
        status = "成功"  # 默认解压状态

        try:
            # 根据解压模式确定目标目录
            if extract_mode == "direct":
                # 平铺解压到文件上层目录
                target_dir = os.path.dirname(os.path.dirname(file_path))
            elif extract_mode == "nested":
                # 分层解压到文件上层目录
                target_dir = self._create_extract_folder(file_path)
            else:
                self.logger.warning(f"未知的解压模式: {extract_mode}")
                return

            # 解压文件
            file_ext = os.path.splitext(file_path)[1]
            self.supported_extensions.get(file_ext, lambda x, y: None)(file_path, target_dir)

            # 删除原压缩文件
            os.remove(file_path)
            self.logger.info(f"删除原文件 {file_path}")

        except Exception as e:
            status = f"失败: {e}"
            self.logger.error(f"处理文件 {file_path} 时出错: {e}")

        # 发送钉钉通知
        self._send_dingtalk_message(webhook_url, product_line, file_name, extract_mode, status)

    def _send_dingtalk_message(self, webhook_url, product_line, file_name, extract_mode, status):
        """
        发送钉钉通知

        :param webhook_url: 钉钉 Webhook URL
        :param product_line: 产品线名称
        :param file_name: 文件名称
        :param extract_mode: 解压模式（平铺解压/分层解压）
        :param status: 解压状态
        """
        try:
            # 将解压模式映射到中文描述
            mode_map = {"direct": "平铺解压", "nested": "分层解压"}
            mode_desc = mode_map.get(extract_mode, "未知模式")

            # 使用 MarkdownTableWriter 生成表格
            writer = MarkdownTableWriter(
                table_name="解压通知",
                headers=["**产品线**", "**文件名**", "**解压模式**", "**解压状态**"],
                value_matrix=[[product_line, file_name, mode_desc, status]],
            )
            table = writer.dumps()

            # 生成钉钉消息
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "解压通知",
                    "text": f"{table}"
                }
            }

            response = requests.post(webhook_url, json=message)
            self.logger.info(f"钉钉通知: {response.status_code}, 内容: {response.text}")

        except Exception as e:
            self.logger.error(f"发送钉钉通知失败: {e}")

    def monitor_directories(self):
        """
        监控配置中指定的目录
        """
        self.logger.info("开始监控目录...")

        # 创建 inotify 监控实例
        i = inotify.adapters.Inotify()

        # 添加要监控的目录及模式映射
        directory_modes = {}
        for product_line in self.config.get('product_lines', []):
            for item in product_line.get('watch_directories', []):
                directory = item.get('path')
                mode = item.get('extract_mode', 'nested')  # 默认使用 nested 模式
                webhook_url = product_line.get('notification', {}).get('dingtalk', {}).get('webhook_url')
                try:
                    i.add_watch(directory)
                    directory_modes[directory] = (mode, product_line['name'], webhook_url)
                    self.logger.info(f"正在监控目录: {directory} (产品线: {product_line['name']}, 模式: {mode})")
                except Exception as e:
                    self.logger.error(f"无法监控目录 {directory}: {e}")

        try:
            for event in i.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event

                if 'IN_CLOSE_WRITE' in type_names:
                    full_path = os.path.join(path, filename)
                    extract_mode, product_line, webhook_url = directory_modes.get(path, ('nested', '', ''))
                    self.process_file(full_path, extract_mode, product_line, webhook_url)

        except KeyboardInterrupt:
            self.logger.info("监控中断")
        except Exception as e:
            self.logger.error(f"监控过程中发生错误: {e}")


def main():
    unzipper = AutoUnzipper()
    unzipper.monitor_directories()


if __name__ == '__main__':
    main()
