#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTML报告生成模块
输出：白底黑字结构化报告，含买点/卖点信号、建仓价、止损价、目标价
"""

import os
from datetime import datetime


def generate_report(results, output_path=None):
    """生成HTML买卖信号报告"""
    if not results:
        return None

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    date_str = datetime.now().strftime('%Y%m%d')

    if output_path is None:
        output_path = f'dividend_buy_sell_{date_str}.html'

    # 统计
    total = len(results)
    strong_buy = [r for r in results if r['buy_score'] >= 60]
    buy = [r for r in results if 45 <= r['buy_score'] < 60]
    watch = [r for r in results if 30 <= r['buy_score'] < 45]
    strong_sell = [r for r in results if r['sell_score'] >= 50]
    sell = [r for r in results if 35 <= r['sell_score'] < 50]

    rows_html = ''
    for i, r in enumerate(results):
        rank = i + 1

        # 买点颜色
        if r['buy_score'] >= 60:
            buy_class = 'buy-strong'
        elif r['buy_score'] >= 45:
            buy_class = 'buy-good'
        elif r['buy_score'] >= 30:
            buy_class = 'buy-watch'
        else:
            buy_class = 'buy-none'

        # 卖点颜色
        if r['sell_score'] >= 50:
            sell_class = 'sell-strong'
        elif r['sell_score'] >= 35:
            sell_class = 'sell-warn'
        elif r['sell_score'] >= 20:
            sell_class = 'sell-caution'
        else:
            sell_class = 'sell-none'

        buy_reasons = '；'.join(r['buy_reasons']) if r['buy_reasons'] else '-'
        sell_reasons = '；'.join(r['sell_reasons']) if r['sell_reasons'] else '-'

        div_str = f"{r['dividend_yield']:.1f}%" if r['dividend_yield'] else '-'
        pe_str = f"{r['pe_ttm']:.1f}" if r['pe_ttm'] else '-'
        entry_str = f"{r['entry_price']:.2f}" if r['entry_price'] else '-'
        stop_str = f"{r['stop_loss']:.2f}" if r['stop_loss'] else '-'
        target_str = f"{r['target_price']:.2f}" if r['target_price'] else '-'
        rsi_str = f"{r['rsi']:.0f}" if r['rsi'] else '-'

        # 安全边际
        if r['entry_price'] and r['close']:
            margin = (1 - r['entry_price'] / r['close']) * 100
            margin_str = f"{margin:+.1f}%"
            if margin > 20:
                margin_class = 'margin-deep'
            elif margin > 0:
                margin_class = 'margin-ok'
            elif margin > -10:
                margin_class = 'margin-warn'
            else:
                margin_class = 'margin-bad'
        else:
            margin_str = '-'
            margin_class = ''

        rows_html += f'''<tr>
            <td>{rank}</td>
            <td>{r['code']}</td>
            <td class="n">{r['name']}</td>
            <td class="r">{r['close']:.2f}</td>
            <td class="r">{pe_str}</td>
            <td class="r">{div_str}</td>
            <td class="{buy_class}">{r['buy_label']}</td>
            <td class="r entry">{entry_str}</td>
            <td class="r">{stop_str}</td>
            <td class="r target">{target_str}</td>
            <td class="r {margin_class}">{margin_str}</td>
            <td class="{sell_class}">{r['sell_label']}</td>
            <td class="l signal-reason">{buy_reasons}</td>
        </tr>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>红利组合买卖信号 - {now}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:"Microsoft YaHei","PingFang SC",sans-serif; background:#fff; color:#1a1a1a; padding:20px; }}
.container {{ max-width:1500px; margin:0 auto; }}
h1 {{ text-align:center; font-size:22px; margin-bottom:2px; }}
.subtitle {{ text-align:center; font-size:12px; color:#888; margin-bottom:16px; }}
.stats {{ display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-bottom:16px; }}
.stat {{ background:#f5f5f5; padding:10px 18px; font-size:12px; text-align:center; min-width:90px; }}
.stat b {{ font-size:18px; }}
.buy-s {{ color:#c00; }}
.buy-g {{ color:#e67e22; }}
.buy-w {{ color:#666; }}
.sell-s {{ color:#c00; }}
.sell-w {{ color:#e67e22; }}
.legend {{ font-size:11px; color:#555; margin-bottom:14px; line-height:1.8; background:#fafafa; padding:10px 14px; border-left:3px solid #333; }}
table {{ border-collapse:collapse; width:100%; font-size:12px; }}
th {{ background:#222; color:#fff; padding:9px 6px; text-align:center; border:1px solid #444; position:sticky; top:0; z-index:1; }}
td {{ padding:5px 6px; border:1px solid #ccc; text-align:center; }}
tr:nth-child(even) {{ background:#f9f9f9; }}
tr:hover {{ background:#e8e8e8; }}
.n {{ text-align:left; font-weight:500; }}
.r {{ text-align:right; font-family:Consolas,monospace; }}
.l {{ text-align:left; }}
.signal-reason {{ font-size:11px; color:#555; max-width:220px; }}
.entry {{ color:#c0392b; font-weight:bold; }}
.target {{ color:#27ae60; font-weight:bold; }}
.buy-strong {{ background:#ffe0e0; color:#c0392b; font-weight:bold; font-size:13px; }}
.buy-good {{ background:#fff3e0; color:#e67e22; font-weight:bold; }}
.buy-watch {{ background:#ffebee; color:#666; }}
.buy-none {{ color:#aaa; }}
.sell-strong {{ background:#ffe0e0; color:#c0392b; font-weight:bold; }}
.sell-warn {{ background:#fff3e0; color:#e67e22; font-weight:bold; }}
.sell-caution {{ color:#f39c12; }}
.sell-none {{ color:#aaa; }}
.margin-deep {{ color:#27ae60; font-weight:bold; }}
.margin-ok {{ color:#2ecc71; }}
.margin-warn {{ color:#e67e22; }}
.margin-bad {{ color:#c0392b; }}
.footer {{ text-align:center; margin-top:16px; color:#aaa; font-size:11px; border-top:1px solid #eee; padding-top:12px; }}
</style>
</head>
<body>
<div class="container">
<h1>红利组合 - 买卖信号日报</h1>
<p class="subtitle">技术指标 + 股息率双因子驱动 | PE∈(0,20] + 分红融资比&gt;1 | {now}</p>

<div class="stats">
  <div class="stat">分析标的<b>{total}</b>只</div>
  <div class="stat buy-s">强烈买入<b>{len(strong_buy)}</b></div>
  <div class="stat buy-g">买入<b>{len(buy)}</b></div>
  <div class="stat buy-w">关注<b>{len(watch)}</b></div>
  <div class="stat sell-s">强烈卖出<b>{len(strong_sell)}</b></div>
  <div class="stat sell-w">卖出建议<b>{len(sell)}</b></div>
</div>

<div class="legend">
  <b>买点规则</b>: 股息率≥6%(30分) + PE≤8(15分) + 价格≤MA60(10分) + RSI&lt;40(10分) + MACD金叉(10分) + KDJ金叉(10分) + 布林下轨(10分)<br>
  <b>卖点规则</b>: RSI&gt;70(25分) + MACD死叉(25分) + KDJ死叉(15分) + 布林上轨(15分) + 偏离MA20(10分) + 空头排列(10分)<br>
  <b>建仓价</b> = 现价 × 当前股息率 ÷ 6%目标股息率 | <b>止损价</b> = 建仓价 × 0.92 | <b>目标价</b> = 建仓价 × 6% ÷ 4% = 建仓价 × 1.5<br>
  <b>安全边际</b>: 正值=现价低于建仓价有利 | 负值=需等回调至建仓价以下
</div>

<table>
<thead><tr>
  <th>#</th>
  <th>代码</th>
  <th>名称</th>
  <th>现价</th>
  <th>PE</th>
  <th>股息率</th>
  <th>买点信号</th>
  <th>建仓价</th>
  <th>止损价</th>
  <th>目标价</th>
  <th>安全边际</th>
  <th>卖点信号</th>
  <th>买点理由</th>
</tr></thead>
<tbody>
{rows_html}
</tbody>
</table>

<p class="footer">
  ⚠️ 本报告为量化模型自动生成，不构成投资建议。买/卖信号基于技术指标+股息率双因子综合评分，请结合基本面判断。<br>
  数据源: akshare(东方财富) | 生成时间: {now} | 代码: dividend-buy-sell
</p>
</div>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"报告已生成: {output_path}")
    print(f"  共{total}只 | 强烈买入{len(strong_buy)} | 买入{len(buy)} | 关注{len(watch)}")
    print(f"  强烈卖出{len(strong_sell)} | 卖出建议{len(sell)}")

    return output_path


def generate_signal_summary(results):
    """生成简要信号汇总（用于邮件正文）"""
    strong_buy = [r for r in results if r['buy_score'] >= 60]
    buy = [r for r in results if 45 <= r['buy_score'] < 60]
    strong_sell = [r for r in results if r['sell_score'] >= 50]

    lines = []
    lines.append(f"红利组合买卖信号日报 - {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"分析标的: {len(results)} 只")
    lines.append("")

    if strong_buy:
        lines.append("【强烈买入 ★★★】")
        for r in strong_buy[:10]:
            entry = f"{r['entry_price']:.2f}" if r['entry_price'] else '-'
            div = f"{r['dividend_yield']:.1f}%" if r['dividend_yield'] else '-'
            lines.append(f"  {r['code']} {r['name']} 现价{r['close']:.2f} 股息率{div} 建仓{entry}")
        lines.append("")

    if buy:
        lines.append("【买入 ★★】")
        for r in buy[:10]:
            entry = f"{r['entry_price']:.2f}" if r['entry_price'] else '-'
            div = f"{r['dividend_yield']:.1f}%" if r['dividend_yield'] else '-'
            lines.append(f"  {r['code']} {r['name']} 现价{r['close']:.2f} 股息率{div} 建仓{entry}")
        lines.append("")

    if strong_sell:
        lines.append("【强烈卖出 ●●●】")
        for r in strong_sell[:10]:
            target = f"{r['target_price']:.2f}" if r['target_price'] else '-'
            lines.append(f"  {r['code']} {r['name']} 现价{r['close']:.2f} 目标{target}")
        lines.append("")

    lines.append("---")
    lines.append("完整报告见附件 | 股息率≥6%+技术指标驱动 | 仅供参考")

    return '\n'.join(lines)
