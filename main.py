import os
from datetime import datetime

import logbook
from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np

app = Flask('StatsWeb')
log = logbook
DATA = {
    'df': None,
    'select_cols': [],
    'sum_cols': [],
}


def _setup(stream):
    global DATA
    df = pd.read_excel(stream, header=1).fillna(method='pad')
    df = df.drop(
        df[df['年月'].apply(lambda x: not isinstance(x, datetime))].index)
    df = df.drop(df[df['区域'].apply(lambda x: '总' in x)].index)
    df['年月'] = df['年月'].apply(lambda x: x.strftime('%Y-%m-%d'))
    df['专营店简称'] = df['区域'] + ' ' + df['专营店简称']
    DATA['df'] = df
    DATA['select_cols'] = [
        DATA['df'].columns[i]
        for i, dt in enumerate(DATA['df'].dtypes)
        if dt == np.dtype('object')]
    DATA['sum_cols'] = [
        DATA['df'].columns[i]
        for i, dt in enumerate(DATA['df'].dtypes)
        if dt != np.dtype('object')]


@app.route('/')
def index(methods=['GET', 'POST']):
    return render_template('index.html')


@app.route('/api/upload', methods=['GET', 'POST'])
def api_upload():
    ufile = request.files
    obj = ufile['file']
    _setup(obj)
    return render_template('index.html')


@app.route('/api/selectors')
def api_selector():
    """{
        selectors: [{
            name: '',
            values: [],
        }]
    }
    """
    if DATA['df'] is not None:
        selectors = []
        for col in DATA['select_cols']:
            selectors.append({
                'name': col,
                'values': DATA['df'][col].unique().tolist(),
            })
    else:
        selectors = None
    return jsonify(**{
        'selectors': selectors,
    })


@app.route('/api/describe')
def api_describe():
    """{
        tables: [{
            name: '总计',
            columns: [],
            rows: [],
        }],
        charts: [{
            type: 'pie',
            title: '',
            series: [],
        }],
    }
    """
    result = {
        'tables': [],
        'charts': [],
    }
    df = DATA['df']

    # filter
    arg = request.args.get('年月')
    if arg and arg != '全部':
        df = df[df['年月'] == arg]

    arg = request.args.get('区域')
    if arg and arg != '全部':
        df = df[df['区域'] == arg]

    arg = request.args.get('专营店简称')
    arg = arg
    if arg and arg != '全部':
        df = df[df['专营店简称'] == arg]

    # 总计
    _df = df.sum()[DATA['sum_cols']]
    result['tables'].append({
        'name': '总计',
        'columns': _df.index.tolist(),
        'rows': [_df.values.tolist()],
    })

    # 按日期
    _df = df.groupby('年月').sum()[DATA['sum_cols']].reset_index()
    result['tables'].append({
        'name': '按年月',
        'columns': _df.columns.tolist(),
        'rows': _df.to_records(index=False).tolist(),
    })

    # 按区域
    _df = df.groupby('区域').sum()[DATA['sum_cols']].reset_index()
    result['tables'].append({
        'name': '按区域',
        'columns': _df.columns.tolist(),
        'rows': _df.to_records(index=False).tolist(),
    })

    # 图形
    # 按区域的饼图
    _df = df.groupby('区域').sum()[['实际交车']].reset_index()
    result['charts'].append({
        'name': '不同小区域的实际交车比例',
        'type': 'pie',
        'series': [{
            'type': 'pie',
            'name': '不同区域的实际交车比例',
            'data': _df.to_records(index=False).tolist(),
        }],
    })
    # 按照大区域分布的饼图
    _df = df.groupby('区域').sum().reset_index()
    _df['大区域'] = _df['区域'].apply(lambda x: '(' not in x and x[:2] or x)
    _df = _df.groupby('大区域').sum().reset_index()[['大区域', '实际交车']]
    result['charts'].append({
        'name': '不同大区域的实际交车比例',
        'type': 'pie',
        'series': [{
            'type': 'pie',
            'name': '不同区域的实际交车比例',
            'data': _df.to_records(index=False).tolist(),
        }],
    })

    # 柱状图
    df['大区域'] = df['区域'].apply(lambda x: ')' not in x and x[:2] or x)
    xCatetories = df['大区域'].unique().tolist()
    result['charts'].append({
        'col-md': 12,
        'xCatetories': xCatetories,
        'type': 'bar',
        'name': '不同大区目标/实际/预测图例',
        'series': [{
            'name': _col,
            'data': [int(df[df['大区域'] == x][_col].sum()) for x in xCatetories],
        } for _col in [
            '目标交车', '目标提车',
            '实际订单', '实际交车', '实际提车',
            '预测交车', '预测提车',
        ]],
    })
    return jsonify(**result)


def main():
    if os.path.exists('files/data_raw.xlsx'):
        _setup('files/data_raw.xlsx')
    app.run(
        host='0.0.0.0',
        port=9871,
        debug=True,
    )


if __name__ == '__main__':
    main()
