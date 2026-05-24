#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技术指标计算模块
支持：MA, RSI, MACD, ADX, 布林带, KDJ, ATR
数据源：腾讯财经 stock_zh_a_hist_tx (日K线，前复权)
"""

import akshare as ak
import pandas as pd
import numpy as np
import time


def fetch_kline(code, days=250):
    """获取个股K线数据（腾讯财经）"""
    try:
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=days + 30)).strftime('%Y%m%d')
        end_date = pd.Timestamp.now().strftime('%Y%m%d')

        # 沪市: sh前缀, 深市: sz前缀
        if code.startswith(('60', '68')):
            symbol = f'sh{code}'
        else:
            symbol = f'sz{code}'

        df = ak.stock_zh_a_hist_tx(symbol=symbol, start_date=start_date, end_date=end_date)
        if df is None or len(df) < 60:
            return None

        # 统一列名
        df = df.rename(columns={
            'date': '日期', 'open': '开盘', 'close': '收盘',
            'high': '最高', 'low': '最低', 'amount': '成交额'
        })
        return df
    except Exception as e:
        return None


def calc_ma(df, periods=[5, 10, 20, 60]):
    """计算移动平均线"""
    for p in periods:
        df[f'MA{p}'] = df['收盘'].rolling(window=p).mean()
    return df


def calc_rsi(df, period=14):
    """计算RSI"""
    delta = df['收盘'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    return df


def calc_macd(df, fast=12, slow=26, signal=9):
    """计算MACD"""
    ema_fast = df['收盘'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['收盘'].ewm(span=slow, adjust=False).mean()
    df['MACD_DIF'] = ema_fast - ema_slow
    df['MACD_DEA'] = df['MACD_DIF'].ewm(span=signal, adjust=False).mean()
    df['MACD_HIST'] = 2 * (df['MACD_DIF'] - df['MACD_DEA'])
    return df


def calc_bollinger(df, period=20, std=2):
    """计算布林带"""
    ma = df['收盘'].rolling(window=period).mean()
    std_dev = df['收盘'].rolling(window=period).std()
    df['BOLL_MID'] = ma
    df['BOLL_UP'] = ma + std * std_dev
    df['BOLL_DN'] = ma - std * std_dev
    df['BOLL_WIDTH'] = (df['BOLL_UP'] - df['BOLL_DN']) / df['BOLL_MID'] * 100
    return df


def calc_atr(df, period=14):
    """计算ATR"""
    high, low, close = df['最高'], df['最低'], df['收盘'].shift(1)
    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=period).mean()
    return df


def calc_kdj(df, period=9):
    """计算KDJ"""
    low_min = df['最低'].rolling(window=period).min()
    high_max = df['最高'].rolling(window=period).max()
    rsv = (df['收盘'] - low_min) / (high_max - low_min).replace(0, np.nan) * 100
    df['KDJ_K'] = rsv.ewm(alpha=1/3, adjust=False).mean()
    df['KDJ_D'] = df['KDJ_K'].ewm(alpha=1/3, adjust=False).mean()
    df['KDJ_J'] = 3 * df['KDJ_K'] - 2 * df['KDJ_D']
    return df


def calc_adx(df, period=14):
    """计算ADX"""
    high, low, close = df['最高'], df['最低'], df['收盘']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    plus_dm = high.diff()
    minus_dm = -(low.diff())
    plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > minus_dm.abs()), 0.0)
    minus_dm = minus_dm.where((minus_dm > 0) & (minus_dm > plus_dm), 0.0)

    atr_smooth = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr_smooth.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr_smooth.replace(0, np.nan))
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    df['ADX'] = dx.ewm(alpha=1/period, adjust=False).mean()
    df['ADX_PDI'] = plus_di
    df['ADX_MDI'] = minus_di
    return df


def calc_all_indicators(code, days=250):
    """计算所有技术指标"""
    df = fetch_kline(code, days=days)
    if df is None or len(df) < 60:
        return None

    df = calc_ma(df)
    df = calc_rsi(df)
    df = calc_macd(df)
    df = calc_bollinger(df)
    df = calc_atr(df)
    df = calc_kdj(df)
    df = calc_adx(df)

    # 涨跌幅
    df['pct_change'] = df['收盘'].pct_change() * 100

    status = get_price_status(df)
    signals = get_indicator_signals(df)

    return df, status, signals


def get_price_status(df):
    """获取当前价格相对于各指标的状态"""
    latest = df.iloc[-1]
    close = latest['收盘']

    status = {
        'close': round(close, 2),
        'change_pct': round(latest.get('pct_change', 0), 2),
        'ma5': round(latest.get('MA5', close), 2),
        'ma10': round(latest.get('MA10', close), 2),
        'ma20': round(latest.get('MA20', close), 2),
        'ma60': round(latest.get('MA60', close), 2),
        'rsi': round(latest.get('RSI', 50), 1),
        'macd_dif': round(latest.get('MACD_DIF', 0), 3),
        'macd_dea': round(latest.get('MACD_DEA', 0), 3),
        'macd_hist': round(latest.get('MACD_HIST', 0), 3),
        'kdj_k': round(latest.get('KDJ_K', 50), 1),
        'kdj_d': round(latest.get('KDJ_D', 50), 1),
        'kdj_j': round(latest.get('KDJ_J', 50), 1),
        'boll_mid': round(latest.get('BOLL_MID', close), 2),
        'boll_up': round(latest.get('BOLL_UP', close), 2),
        'boll_dn': round(latest.get('BOLL_DN', close), 2),
        'adx': round(latest.get('ADX', 20), 1),
        'atr': round(latest.get('ATR', 0), 2),
    }

    # 价格偏离MA的百分比
    for p in [5, 10, 20, 60]:
        ma_val = latest.get(f'MA{p}', close)
        if ma_val and ma_val > 0:
            status[f'dev_ma{p}'] = round((close / ma_val - 1) * 100, 1)

    return status


def get_indicator_signals(df):
    """获取指标信号"""
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    signals = []
    close = latest['收盘']

    # MA信号
    if pd.notna(latest.get('MA5')) and close > latest['MA5']:
        signals.append('MA5↑')
    elif pd.notna(latest.get('MA5')):
        signals.append('MA5↓')

    # 均线多头/空头排列
    ma_list = ['MA5', 'MA10', 'MA20', 'MA60']
    ma_values = [latest.get(m) for m in ma_list if pd.notna(latest.get(m))]
    if len(ma_values) >= 3:
        if all(ma_values[i] > ma_values[i+1] for i in range(len(ma_values)-1)):
            signals.append('多头排列')
        elif all(ma_values[i] < ma_values[i+1] for i in range(len(ma_values)-1)):
            signals.append('空头排列')

    # RSI
    if pd.notna(latest.get('RSI')):
        rsi = latest['RSI']
        if rsi < 30:
            signals.append('RSI超卖')
        elif rsi > 70:
            signals.append('RSI超买')
        elif rsi > 50:
            signals.append('RSI偏强')
        else:
            signals.append('RSI偏弱')

    # MACD
    if pd.notna(latest.get('MACD_DIF')) and pd.notna(latest.get('MACD_DEA')):
        now_cross_up = latest['MACD_DIF'] > latest['MACD_DEA'] and prev['MACD_DIF'] <= prev['MACD_DEA']
        now_cross_dn = latest['MACD_DIF'] < latest['MACD_DEA'] and prev['MACD_DIF'] >= prev['MACD_DEA']
        if now_cross_up:
            signals.append('MACD金叉')
        elif now_cross_dn:
            signals.append('MACD死叉')
        elif latest['MACD_HIST'] > prev['MACD_HIST'] and latest['MACD_HIST'] > 0:
            signals.append('MACD红柱放大')
        elif latest['MACD_HIST'] < prev['MACD_HIST'] and latest['MACD_HIST'] < 0:
            signals.append('MACD绿柱放大')

    # KDJ
    if pd.notna(latest.get('KDJ_J')) and pd.notna(prev.get('KDJ_J')):
        if latest['KDJ_J'] < 0:
            signals.append('KDJ超卖')
        elif latest['KDJ_J'] > 100:
            signals.append('KDJ超买')
        if latest['KDJ_K'] > latest['KDJ_D'] and prev['KDJ_K'] <= prev['KDJ_D']:
            signals.append('KDJ金叉')
        elif latest['KDJ_K'] < latest['KDJ_D'] and prev['KDJ_K'] >= prev['KDJ_D']:
            signals.append('KDJ死叉')

    # 布林带
    if pd.notna(latest.get('BOLL_DN')) and close <= latest['BOLL_DN']:
        signals.append('触及布林下轨')
    elif pd.notna(latest.get('BOLL_UP')) and close >= latest['BOLL_UP']:
        signals.append('触及布林上轨')

    # ADX
    if pd.notna(latest.get('ADX')) and latest['ADX'] > 25:
        if pd.notna(latest.get('ADX_PDI')) and latest['ADX_PDI'] > latest['ADX_MDI']:
            signals.append('ADX多头趋势')
        else:
            signals.append('ADX空头趋势')

    return signals


if __name__ == '__main__':
    code = '601398'
    print(f"测试 {code} 技术指标...\n")
    result = calc_all_indicators(code)
    if result:
        df, status, sigs = result
        print("=== 技术状态 ===")
        for k, v in status.items():
            print(f"  {k}: {v}")
        print(f"\n=== 指标信号 ({len(sigs)}个) ===")
        for s in sigs:
            print(f"  • {s}")
    else:
        print("获取数据失败")
