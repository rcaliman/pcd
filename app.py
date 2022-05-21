from flask import Flask, render_template, request
from numpy_financial import rate, pv
from datetime import datetime, date, timedelta
from time import strftime
from os.path import isfile
from contextlib import closing
import requests
import sqlite3
import csv

app = Flask(__name__)


def datas_exemplos() -> dict:
    proxima_data = (datetime.now() + timedelta(days=5)).strftime("%d%m%Y")
    ultima_data = (datetime.now() + timedelta(days=706)).strftime("%d%m%Y")
    return {'proxima_data': proxima_data, 'ultima_data': ultima_data}

def busca_ultimo_registro() -> tuple:
    with closing(sqlite3.connect('pcd.db')) as conn:
        with closing(conn) as cur:
            query = """ select * from pcd order by id desc limit 1"""
            dados = cur.execute(query).fetchall()
            return dados[0]

def busca_total_calculos_diarios() -> int:
    with closing(sqlite3.connect('pcd.db')) as conn:
        with closing(conn) as cur:
            query = f"""select count(*) from pcd where data_calculo = '{strftime('%Y-%m-%d')}';"""
            dados = cur.execute(query).fetchall()
            return dados[0][0]

def baixa_bancos():
    arquivo = requests.get('http://www.bcb.gov.br/pom/spb/ing/ParticipantesSTRIng.CSV')
    data_ultimo = busca_ultimo_registro()[1]
    data_atual = strftime('%Y-%m-%d')
    nao_atualizado = data_atual > data_ultimo
    nao_existe = not(isfile('bancos.csv'))
    if nao_atualizado or nao_existe:
        if arquivo.status_code == 200:
            f = open('bancos.csv', 'w')
            f.write(str(arquivo.content.decode('utf-8')))
            f.close()



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
    if len(_banco) == 1:
        _banco = '00' + _banco
    elif len(_banco) == 2:
        _banco = '0' + _banco

    with open('bancos.csv', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for linha in reader:
            try:
                if linha[2] == _banco:
                    return {'ispb': linha[0], 'nome': linha[5]}
            except Exception:
                pass
        return {'ispb': 'não encontrado', 'nome': 'não encontrado'}

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
    baixa_bancos()
    return render_template('inicio.html',
                            quantidade_calculos = busca_total_calculos_diarios(),
                            datas_exemplos = datas_exemplos()
                            )


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
        return  f""" 
                    <center>
                        <table>                                
                            <tr>
                                 <td style='background-color: red; color: white; padding-top:15px;'>
                                    <h3 style='padding-left: 10px; padding-right: 10px;'>
                                        erro: por favor volte e confira se os campos foram preenchidos conforme as indicações.
                                    </h3>
                                    <center>
                                        <p>
                                            {e}
                                        </p>
                                    </center>
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
