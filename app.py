from flask import Flask, render_template, request
from numpy_financial import rate, pv
from datetime import date
import csv

app = Flask(__name__)


def formata_data(data):
    dia, mes, ano = int(data[:2]), int(data[2:4]), int(data[4:])
    return date(ano, mes, dia)


def calcula_meses(data_menor, data_maior):
    return (data_maior.year - data_menor.year) * 12 + 1 + data_maior.month - data_menor.month


def busca_ispb(_banco):
    with open('bancos.csv', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for linha in reader:
            if linha[0] == _banco:
                return f'{linha[1]}\t{linha[2]}'


def formata_valor(_valor):
    return float(f'{_valor[:-2]}.{_valor[-2:]}')


@app.route('/')
def inicio():
    return render_template('inicio.html')


@app.route('/calculo', methods=['POST'])
def calculo():
    contrato = request.form.get('contrato')
    banco = request.form.get('banco')
    data_ultima_parcela = formata_data(request.form.get('data_ultima_parcela'))
    quantidade_de_parcelas = int(request.form.get('quantidade_de_parcelas'))
    valor_da_parcela = formata_valor(request.form.get('valor_da_parcela'))
    valor_emprestado = formata_valor(request.form.get('valor_emprestado'))

    hoje = formata_data(date.today().strftime('%d%m%Y'))
    taxa_de_juros = round((rate(quantidade_de_parcelas, -valor_da_parcela, valor_emprestado, 0) * 100), 2)
    meses_em_ser = calcula_meses(hoje, data_ultima_parcela)
    saldo_devedor = pv(taxa_de_juros/100, meses_em_ser, -valor_da_parcela,)
    return render_template('calculo.html',
                           contrato=contrato,
                           banco=busca_ispb(banco),
                           taxa_de_juros=taxa_de_juros,
                           meses_em_ser=meses_em_ser,
                           saldo_devedor=saldo_devedor,
                           )


app.run(host='0.0.0.0', port=5004)
