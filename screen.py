#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
红利股筛选模块
条件：PE∈(0,20] + 分红融资比>1 + 非ST
数据源：腾讯财经 (PE/PB/现价) + akshare (分红融资)

工作流程：
  1. akshare stock_history_dividend → 全A股分红融资比>1名单
  2. 腾讯财经 http://qt.gtimg.cn → 逐个获取PE、PB、现价
  3. 筛选PE∈(0,20] + 非ST
"""

import akshare as ak
import pandas as pd
import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


def fetch_tencent_quotes(codes):
    """批量从腾讯财经获取实时行情 (每批最多50只)"""
    results = {}

    # 构建symbol前缀
    symbols = []
    for c in codes:
        c = str(c).zfill(6)
        if c.startswith(('60', '68')):
            symbols.append(f'sh{c}')
        else:
            symbols.append(f'sz{c}')

    # 分批获取（腾讯API单次建议不超过50只）
    batch_size = 50
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        url = f"http://qt.gtimg.cn/q={','.join(batch)}"
        try:
            resp = requests.get(url, timeout=10)
            resp.encoding = 'gbk'

            for line in resp.text.strip().split('\n'):
                if '="' not in line:
                    continue
                # 格式: v_sh601398="1~工商银行~601398~..."
                m = re.match(r'v_(\w+)="(.+)"', line.strip())
                if not m:
                    continue
                sym, data = m.groups()
                parts = data.split('~')
                if len(parts) < 50:
                    continue

                code = parts[2]
                name = parts[1]
                # [3]=现价, [32]=涨跌幅, [39]=PE, [46]=PB
                try:
                    close = float(parts[3]) if parts[3] else 0
                    change_pct = float(parts[32]) if parts[32] else 0
                    pe = float(parts[39]) if parts[39] else None
                    pb = float(parts[46]) if parts[46] else None
                except (ValueError, IndexError):
                    continue

                if close <= 0:
                    continue

                results[code] = {
                    'code': code, 'name': name, 'close': close,
                    'pe_ttm': pe, 'pb': pb, 'change_pct': change_pct,
                }
        except Exception:
            continue

    return results


def screen_dividend_stocks():
    """
    筛选符合条件的红利股
    返回 DataFrame
    """
    print("=" * 60)
    print("红利股筛选: PE∈(0,20] + 分红融资比>1 + 非ST")
    print("=" * 60)

    # Step 1: 分红融资数据
    print("[Screen/1] 获取分红融资数据...", end=' ', flush=True)
    for attempt in range(3):
        try:
            df_div = ak.stock_history_dividend()
            if len(df_div) > 0:
                break
        except Exception:
            if attempt < 2:
                time.sleep(5)
    print(f"{len(df_div)}只")

    # 统一列名
    cols = df_div.columns.tolist()
    code_col = [c for c in cols if '代码' in c][0]
    name_col = [c for c in cols if '名称' in c][0] if any('名称' in c for c in cols) else cols[1]
    cum_col = [c for c in cols if '累计' in c][0] if any('累计' in c for c in cols) else cols[2]
    fin_col = [c for c in cols if '融资' in c][0] if any('融资' in c for c in cols) else cols[3]
    ratio_col = [c for c in cols if '比' in c][0] if any('比' in c for c in cols) else cols[5]

    df_div = df_div.rename(columns={
        code_col: 'code', name_col: 'name',
        cum_col: 'cum_dividend', fin_col: 'total_finance',
        ratio_col: 'div_ratio',
    })

    df_div['code'] = df_div['code'].astype(str).str[:6]
    df_div = df_div[df_div['code'].str.match(r'^(60|00|30)')]  # 沪深A股
    df_div['div_ratio'] = pd.to_numeric(df_div['div_ratio'], errors='coerce')
    df_div = df_div[df_div['div_ratio'] > 1]
    df_div = df_div[~df_div['name'].str.contains('ST|退', na=False)]
    print(f"  分红融资比>1: {len(df_div)} 只")

    # Step 2: 腾讯财经获取PE
    print(f"[Screen/2] 腾讯财经获取PE...", flush=True)
    codes = df_div['code'].unique().tolist()
    quotes = fetch_tencent_quotes(codes)
    print(f"  获取行情: {len(quotes)} 只")

    # Step 3: PE筛选
    print(f"[Screen/3] PE筛选...", flush=True)
    results = []
    for _, row in df_div.iterrows():
        code = row['code']
        if code not in quotes:
            continue
        q = quotes[code]
        pe = q['pe_ttm']
        if pe is None or pe <= 0 or pe > 20:
            continue

        name = q['name']
        # 二次过滤ST（腾讯行情名可能不显ST）
        if 'ST' in name or '退' in name:
            continue

        results.append({
            'code': code,
            'name': name,
            'close': q['close'],
            'pe_ttm': round(pe, 1),
            'pb': round(q['pb'], 2) if q['pb'] else None,
            'change_pct': q['change_pct'],
            'div_ratio': round(row['div_ratio'], 2),
            'cum_dividend': round(float(row.get('cum_dividend', 0)), 2),
            'total_finance': round(float(row.get('total_finance', 0)), 2),
        })

    df_result = pd.DataFrame(results)
    if len(df_result) > 0:
        df_result = df_result.sort_values('pe_ttm').reset_index(drop=True)

    print(f"  PE∈(0,20]: {len(df_result)} 只")
    return df_result


if __name__ == '__main__':
    result = screen_dividend_stocks()
    print(f"\n最终候选池: {len(result)} 只")
    if len(result) > 0:
        print("\nTop 20:")
        for i, row in result.head(20).iterrows():
            pe = f"{row['pe_ttm']:.1f}" if row['pe_ttm'] else '-'
            print(f"  {i+1:3d}. {row['code']} {row['name']:<8s}  PE={pe}  现价={row['close']:.2f}  分红比={row['div_ratio']:.2f}")
    result.to_csv('candidate_pool.csv', index=False, encoding='utf-8-sig')
