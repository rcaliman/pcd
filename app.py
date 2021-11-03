from flask import Flask, render_template, request
from numpy_financial import rate, pv
from datetime import date
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


def busca_ispb(_banco):
    """
    busca o numero ispb no arquivo bancos.csv que busquei no site do banco central e formatei para o app
    :param _banco: str
    :return: str
    """
    with open('bancos.csv', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for linha in reader:
            if linha[0] == str(int(_banco)):
                return f'{linha[1]}\t{linha[2]}'


def formata_valor(_valor):
    """
    formata a string do valor para ser convertida para float
    :param _valor: str
    :return: float
    """
    return float(f'{_valor[:-2]}.{_valor[-2:]}')


@app.route('/')
def inicio():
    return render_template('inicio.html')


@app.route('/calculo', methods=['POST'])
def calculo():
    try:
        banco = request.form.get('banco')
        data_primeira_parcela = formata_data(request.form.get('data_primeira_parcela'))
        data_ultima_parcela = formata_data(request.form.get('data_ultima_parcela'))
        quantidade_de_parcelas = int(request.form.get('quantidade_de_parcelas'))
        valor_da_parcela = formata_valor(request.form.get('valor_da_parcela'))
        valor_emprestado = formata_valor(request.form.get('valor_emprestado'))

        # hoje = formata_data(date.today().strftime('%d%m%Y'))
        taxa_de_juros = rate(quantidade_de_parcelas, -valor_da_parcela, valor_emprestado, 0)
        meses_em_ser = calcula_meses(data_primeira_parcela, data_ultima_parcela)
        saldo_devedor = pv(taxa_de_juros/100, meses_em_ser, valor_da_parcela,)

        return render_template('calculo.html',
                               banco=busca_ispb(banco),
                               taxa_de_juros=taxa_de_juros * 100,
                               meses_em_ser=meses_em_ser,
                               saldo_devedor=saldo_devedor,
                               )
    except:
        return 'Desculpe-me mas você provavelmente digitou algum dado incorretamente. Retorne e confira.'


app.run(host='0.0.0.0', port=5004)
#app.run(port=5004, debug=True)
