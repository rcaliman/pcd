from flask import Flask, render_template, request
from numpy_financial import rate, pv
from datetime import date
from contextlib import closing
import sqlite3
import csv

app = Flask(__name__)


def formata_data(data: str) -> date:
    """
    recebe a string de data no formato DDMMAA e retorna um tipo date
    :param data: str
    :return: date
    """
    dia, mes, ano = int(data[:2]), int(data[2:4]), int(data[4:])
    return date(ano, mes, dia)


def calcula_meses(data_menor: date, data_maior: date):
    """
    calcula a quantidade de meses do dia atual até a ultima parcela
    :param data_menor: date
    :param data_maior: date
    :return: int
    """
    return (data_maior.year - data_menor.year) * 12 + 1 + data_maior.month - data_menor.month


def busca_ispb(_banco: str) -> dict:
    """
    busca o numero ispb no arquivo bancos.csv que busquei no site do banco central e formatei para o app
    :param _banco: str
    :return: str
    """
    with open('bancos.csv', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for linha in reader:
            if linha[0] == str(int(_banco)):
                return {'ispb': linha[1], 'nome': linha[2]}


def formata_valor(_valor: str) -> float:
    """
    formata a string do valor para ser convertida para float
    :param _valor: str
    :return: float
    """
    return float(f'{_valor[:-2]}.{_valor[-2:]}')


def str_to_date(_data: str) -> str:
    """
    formata a string da data para um formato que possa ser inserido no banco como date
    :param _data: str
    :return: str
    """
    return str(_data)[-4:] + '-' + str(_data)[-6:-4] + '-' + str(_data)[:-6]


def insere_valores(_dados: tuple) -> None:
    with closing(sqlite3.connect('pcd.db')) as conn:
        _dados_tratados = str_to_date(_dados[0]), str_to_date(_dados[1]), _dados[2], _dados[3], \
                          _dados[4], _dados[5], _dados[6], _dados[7]
        with conn as cur:
            query_inserir = '''insert into pcd(data_calculo, proxima_parcela,
                ultima_parcela, quantidade_de_parcelas, valor_da_parcela, valor_emprestado,
                taxa_de_juros, meses_em_ser, saldo_devedor)
                values(date(), '{}', '{}', {}, {}, {}, {}, {}, {});'''.format(*_dados_tratados)
            cur.execute(query_inserir)


def busca_calculos() -> list:
    """
    busca os calculos no banco para exibir na página de calculos anteriores
    :return: list
    """
    with closing(sqlite3.connect('pcd.db')) as conn:
        with conn as cur:
            query_buscar = '''select id, data_calculo, proxima_parcela, ultima_parcela,
                quantidade_de_parcelas, valor_da_parcela, valor_emprestado, taxa_de_juros,
                meses_em_ser, saldo_devedor from pcd order by id desc limit 10;'''
            _dados = cur.execute(query_buscar).fetchall()
    return _dados


def date_to_html(_data: str) -> str:
    """
    formata a data para ser inserida na página html
    :param _data: str
    :return: str
    """
    return _data[8:10] + '/' + _data[5:7] + '/' + _data[:4]


def html_calculos_anteriores() -> str:
    """
    monta as células da tabela para exibir cálculos anteriores
    :return: str
    """
    html = ''
    for i in busca_calculos():
        html += '<tr>'
        html += '<td>' + date_to_html(str(i[1])) + '</td>'
        html += '<td>' + date_to_html(str(i[2])) + '</td>'
        html += '<td>' + date_to_html(str(i[3])) + '</td>'
        html += '<td>' + str(i[4]) + '</td>'
        html += '<td>' + str(round(i[5], 2)).replace('.', ',') + '</td>'
        html += '<td>' + str(round(i[6], 2)).replace('.', ',') + '</td>'
        html += '<td>' + str(round(i[7], 2)).replace('.', ',') + '</td>'
        html += '<td>' + str(i[8]) + '</td>'
        html += '<td>' + str(round(i[9], 2)).replace('.', ',') + '</td>'
        html += '</tr>'
    return html


@app.route('/')
def inicio():
    return render_template('inicio.html')


@app.route('/calculo', methods=['POST'])
def calculo():
    try:
        banco = request.form.get('banco')
        data_proxima_parcela = formata_data(request.form.get('data_proxima_parcela'))
        data_ultima_parcela = formata_data(request.form.get('data_ultima_parcela'))
        quantidade_de_parcelas = int(request.form.get('quantidade_de_parcelas'))
        valor_da_parcela = formata_valor(request.form.get('valor_da_parcela'))
        valor_emprestado = formata_valor(request.form.get('valor_emprestado'))
        taxa_de_juros = rate(quantidade_de_parcelas, -valor_da_parcela, valor_emprestado, 0)
        meses_em_ser = calcula_meses(data_proxima_parcela, data_ultima_parcela)
        saldo_devedor = abs(pv(taxa_de_juros, meses_em_ser, valor_da_parcela, ))
        dados_banco = request.form.get('data_proxima_parcela'), request.form.get('data_ultima_parcela'), \
            quantidade_de_parcelas, valor_da_parcela, valor_emprestado, taxa_de_juros * 100, \
            meses_em_ser, saldo_devedor
        insere_valores(dados_banco)

        return render_template('calculo.html',
                               banco=busca_ispb(banco),
                               taxa_de_juros=taxa_de_juros * 100,
                               meses_em_ser=meses_em_ser,
                               saldo_devedor=saldo_devedor,
                               )
    except Exception as e:
        if 'day' or 'month' or 'year' in char(e):
             return """ 
                        <center>
                            <table>
                                <tr>
                                    <td style='background-color: red; color: white; padding-top:15px;'>
                                        <h3 style='padding-left: 10px; padding-right: 10px;'>
                                            erro: por favor volte e confira os campos de data.
                                        </h3>
                                    </td>
                                </tr>
                            </table>
                        </center>
                   """
        else:
            return """ 
                        <center>
                            <table>
                                <tr>
                                    <td style='background-color: red; color: white; padding-top:15px;'>
                                        <h3 style='padding-left: 10px; padding-right: 10px;'>
                                            erro: por favor volte e confira se os campos foram preenchidos conforme as indicações.
                                        </h3>
                                    </td>
                                </tr>
                            </table>
                        </center>
                   """


@app.route('/buscar_ispb', methods=['POST'])
def buscar_ispb():
    banco = busca_ispb(request.form.get('codigo_banco'))
    return render_template('ispb.html',
                           banco=banco)


@app.route('/calculos_anteriores', methods=['GET'])
def calculos_anteriores():
    return render_template('calculos_anteriores.html',
                           calculos=html_calculos_anteriores())


# app.run(host='0.0.0.0', port=5004)
app.run(port=5004, debug=False, host='0.0.0.0')
