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


@app.route('/')
def index(methods=['GET', 'POST']):
    return render_template('index.html')


@app.route('/api/upload', methods=['GET', 'POST'])
def api_upload():
    global DATA
    ufile = request.files
    obj = ufile['file']
    df = pd.read_excel(obj, header=1).fillna(method='pad')
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
    # 总计
    df = DATA['df']
    _df = df.sum()[DATA['sum_cols']]
    result['tables'].append({
        'name': '总计',
        'columns': _df.index.tolist(),
        'rows': _df.values.tolist(),
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
    return jsonify(**result)


def main():
    app.run(
        host='0.0.0.0',
        port=9871,
        debug=True,
    )


if __name__ == '__main__':
    main()
