#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
红利组合买卖信号系统 - 主流程
串联：筛选 → 技术指标 → 买卖信号 → 报告生成 → 邮件发送

用法：
  python main.py              # 完整流程
  python main.py --test       # 测试模式（前20只）
  python main.py --send       # 发送邮件
  python main.py --test --send  # 测试+发邮件
"""

import sys
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

from screen import screen_dividend_stocks
from buy_sell import batch_analyze
from report import generate_report, generate_signal_summary


# ===================== 配置 =====================
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.qq.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '1293080722@qq.com')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
TO_EMAIL = os.environ.get('TO_EMAIL', '1293080722@qq.com')

TEST_MODE = '--test' in sys.argv
SEND_EMAIL = '--send' in sys.argv

MAX_STOCKS = 30 if TEST_MODE else 300


def send_email_report(report_path, summary):
    """发送邮件报告"""
    if not SMTP_PASS:
        print("未设置SMTP_PASS，跳过邮件发送")
        return False

    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"【红利买卖信号日报】{datetime.now().strftime('%Y-%m-%d')}"
        msg['From'] = SMTP_USER
        msg['To'] = TO_EMAIL
        msg.attach(MIMEText(summary, 'plain', 'utf-8'))

        with open(report_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                            f'attachment; filename="buy_sell_{datetime.now().strftime("%Y%m%d")}.html"')
            msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        print("邮件发送成功!")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False


def main():
    print("=" * 60)
    print("  红利组合买卖信号系统")
    print(f"  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  模式: {'测试(' + str(MAX_STOCKS) + '只)' if TEST_MODE else '全量'}")
    print(f"  邮件: {'发送' if SEND_EMAIL else '不发送'}")
    print("=" * 60)

    # Step 1: 筛选
    print("\n[Step 1/3] 红利股筛选...")
    candidates = screen_dividend_stocks()

    if len(candidates) == 0:
        print("无符合条件的标的，退出")
        return

    # Step 2: 买卖信号分析
    print(f"\n[Step 2/3] 买卖信号分析（最多{MAX_STOCKS}只）...")
    results = batch_analyze(candidates, max_stocks=MAX_STOCKS, sleep_sec=0.3)

    if len(results) == 0:
        print("分析无结果，退出")
        return

    # Step 3: 生成报告
    print("\n[Step 3/3] 生成报告...")
    date_str = datetime.now().strftime('%Y%m%d')
    report_path = f'dividend_buy_sell_{date_str}.html'
    report_path = generate_report(results, output_path=report_path)

    # 邮件
    if SEND_EMAIL and report_path:
        summary = generate_signal_summary(results)
        send_email_report(report_path, summary)

    print(f"\n{'=' * 60}")
    print("运行完成!")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
