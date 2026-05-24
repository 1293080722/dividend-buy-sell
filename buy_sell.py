#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
买卖信号判定模块
基于：技术指标 + 股息率 + 估值水平 → 买点/卖点信号

买点评分:
  股息率≥6% (+30) | ≥5% (+20) | PE≤8 (+15) | PE≤12 (+10)
  价格≤MA60 (+10) | RSI<40 (+10) | RSI<30 (+5 extra)
  MACD金叉 (+10) | MACD红柱放大 (+8)
  KDJ金叉 (+10) | 布林下轨 (+10) | 多头排列 (+5)

卖点评分:
  RSI>70 (+25) | MACD死叉 (+25) | MACD绿柱放大 (+15)
  KDJ死叉 (+15) | KDJ超买 (+10) | 布林上轨 (+15)
  偏离MA20>15% (+10) | 空头排列 (+10) | ADX空头 (+10)

信号等级:
  买: ≥60强烈买入 | ≥45买入 | ≥30关注 | <30观望
  卖: ≥50强烈卖出 | ≥35卖出建议 | ≥20谨慎持有 | <20继续持有
"""

import pandas as pd
import numpy as np
import time
from signals import calc_all_indicators


def calc_dividend_yield(code, close_price):
    """计算TTM股息率：近12个月已实施分红 / 当前股价"""
    import akshare as ak
    try:
        df = ak.stock_history_dividend_detail(symbol=code, indicator='分红')
        if df is None or len(df) == 0:
            return None

        df['公告日期'] = pd.to_datetime(df['公告日期'])
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=365)
        recent = df[(df['公告日期'] >= cutoff) & (df['进度'] == '实施')]

        if len(recent) == 0:
            return None

        # 找派息列
        div_col = None
        for c in ['派息', '每股派息', '税前派息']:
            if c in recent.columns:
                div_col = c
                break
        if div_col is None:
            return None

        total_dps = recent[div_col].astype(float).sum()
        # akshare返回的是每10股派息，需除以10得到每股派息
        dps_per_share = total_dps / 10
        if dps_per_share <= 0 or close_price <= 0:
            return None

        return round(dps_per_share / close_price * 100, 2)
    except Exception:
        return None


def calc_buy_score(status, signals, dividend_yield, pe_ttm):
    """计算买点评分"""
    score = 0
    reasons = []

    if dividend_yield and dividend_yield >= 6:
        score += 30
        reasons.append(f'股息率{dividend_yield}%≥6%')
    elif dividend_yield and dividend_yield >= 5:
        score += 20
        reasons.append(f'股息率{dividend_yield}%≥5%')

    if pe_ttm and pe_ttm <= 8:
        score += 15
        reasons.append(f'PE={pe_ttm:.1f}≤8')
    elif pe_ttm and pe_ttm <= 12:
        score += 10
        reasons.append(f'PE={pe_ttm:.1f}≤12')

    dev_ma60 = status.get('dev_ma60', 999)
    if dev_ma60 is not None and dev_ma60 <= 0:
        score += 10
        reasons.append(f'价≤MA60({dev_ma60:.0f}%)')

    rsi = status.get('rsi', 50)
    if rsi and rsi < 30:
        score += 10
        reasons.append(f'RSI={rsi}超卖')
    elif rsi and rsi < 40:
        score += 5
        reasons.append(f'RSI={rsi}偏低')

    if 'MACD金叉' in signals:
        score += 10
        reasons.append('MACD金叉')
    elif 'MACD红柱放大' in signals:
        score += 8
        reasons.append('MACD红柱放大')

    if 'KDJ金叉' in signals:
        score += 10
        reasons.append('KDJ金叉')

    if '触及布林下轨' in signals:
        score += 10
        reasons.append('触及布林下轨')

    if '多头排列' in signals:
        score += 5
        reasons.append('均线多头排列')

    return score, reasons


def calc_sell_score(status, signals):
    """计算卖点评分"""
    score = 0
    reasons = []

    rsi = status.get('rsi', 50)
    if rsi and rsi > 70:
        score += 25
        reasons.append(f'RSI={rsi}超买')

    if 'MACD死叉' in signals:
        score += 25
        reasons.append('MACD死叉')
    elif 'MACD绿柱放大' in signals:
        score += 15
        reasons.append('MACD绿柱放大')

    if 'KDJ死叉' in signals:
        score += 15
        reasons.append('KDJ死叉')
    elif 'KDJ超买' in signals:
        score += 10
        reasons.append('KDJ超买')

    if '触及布林上轨' in signals:
        score += 15
        reasons.append('触及布林上轨')

    dev_ma20 = status.get('dev_ma20', 0)
    if dev_ma20 and dev_ma20 > 15:
        score += 10
        reasons.append(f'偏离MA20+{dev_ma20:.0f}%')

    if '空头排列' in signals:
        score += 10
        reasons.append('均线空头排列')

    if 'ADX空头趋势' in signals:
        score += 10
        reasons.append('ADX空头趋势')

    return score, reasons


def get_signal_label(buy_score):
    if buy_score >= 60:
        return '★★★ 强烈买入'
    elif buy_score >= 45:
        return '★★ 买入'
    elif buy_score >= 30:
        return '★ 关注'
    return '观望'


def get_sell_label(sell_score):
    if sell_score >= 50:
        return '●●● 强烈卖出'
    elif sell_score >= 35:
        return '●● 卖出建议'
    elif sell_score >= 20:
        return '● 谨慎持有'
    return '继续持有'


def calc_entry_price(close, dividend_yield, target_yield=6.0):
    """建仓价 = 现价 × 当前股息率 / 目标股息率(6%)"""
    if not dividend_yield or dividend_yield <= 0:
        return None
    return round(close * dividend_yield / target_yield, 2)


def calc_stop_loss(entry_price):
    """止损价 = 建仓价 × 0.92"""
    if not entry_price:
        return None
    return round(entry_price * 0.92, 2)


def calc_target_price(entry_price):
    """目标价 = 建仓价 × 6% / 4% = 建仓价 × 1.5"""
    if not entry_price:
        return None
    return round(entry_price * 1.5, 2)


def analyze_stock(code, name, pe_ttm, close_est=None):
    """综合分析单只股票"""
    print(f"  [{code} {name}]", end=' ', flush=True)

    # 技术指标
    result = calc_all_indicators(code)
    if result is None:
        print("K线不足")
        return None
    df, status, signals = result

    close = status['close']
    if close_est and close_est > 0:
        close = close_est

    # 股息率
    dividend_yield = calc_dividend_yield(code, close)

    # 评分
    buy_score, buy_reasons = calc_buy_score(status, signals, dividend_yield, pe_ttm)
    sell_score, sell_reasons = calc_sell_score(status, signals)

    # 价位
    entry_price = calc_entry_price(close, dividend_yield)

    result_dict = {
        'code': code, 'name': name,
        'close': close, 'pe_ttm': pe_ttm,
        'dividend_yield': dividend_yield,
        'buy_score': buy_score,
        'buy_label': get_signal_label(buy_score),
        'buy_reasons': buy_reasons,
        'sell_score': sell_score,
        'sell_label': get_sell_label(sell_score),
        'sell_reasons': sell_reasons,
        'entry_price': entry_price,
        'stop_loss': calc_stop_loss(entry_price),
        'target_price': calc_target_price(entry_price),
        'rsi': status.get('rsi'),
        'macd_hist': status.get('macd_hist'),
        'dev_ma60': status.get('dev_ma60'),
        'signals': signals,
        'status': status,
    }

    buy_tag = result_dict['buy_label'].replace('★', '*')
    sell_tag = result_dict['sell_label'].replace('●', '!')
    print(f"买{buy_score}分/{buy_tag}  卖{sell_score}分/{sell_tag}")
    return result_dict


def batch_analyze(candidates_df, max_stocks=200, sleep_sec=0.3):
    """批量分析"""
    results = []
    df = candidates_df.head(max_stocks)
    total = len(df)

    print(f"\n[批量分析] 共{total}只...")
    for i, (_, row) in enumerate(df.iterrows()):
        code = row['code']
        name = row.get('name', '')
        pe = row.get('pe_ttm')
        print(f"  [{i+1}/{total}]", end=' ')
        res = analyze_stock(code, name, pe)
        if res:
            results.append(res)
        if i < total - 1:
            time.sleep(sleep_sec)

    results.sort(key=lambda x: -x['buy_score'])
    print(f"\n分析完成: {len(results)}/{total} 只有效数据")
    return results


if __name__ == '__main__':
    test_stocks = [
        ('601398', '工商银行', 6.5),
        ('601939', '建设银行', 6.0),
        ('600036', '招商银行', 7.5),
    ]
    for code, name, pe in test_stocks:
        res = analyze_stock(code, name, pe)
        if res:
            print(f"\n  {code} {name}: 现价={res['close']:.2f}, PE={res['pe_ttm']}, 股息率={res['dividend_yield']}%")
            print(f"  买点: {res['buy_label']} ({res['buy_score']}分)")
            if res['buy_reasons']:
                print(f"    → {'; '.join(res['buy_reasons'])}")
            print(f"  卖点: {res['sell_label']} ({res['sell_score']}分)")
            if res['sell_reasons']:
                print(f"    → {'; '.join(res['sell_reasons'])}")
            if res['entry_price']:
                print(f"  建仓={res['entry_price']:.2f}  止损={res['stop_loss']:.2f}  目标={res['target_price']:.2f}")
