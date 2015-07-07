# -*- coding: utf-8 -*-

import os
import sys
import json
import urllib2
import argparse

from calendar import Calendar
from datetime import date, datetime, timedelta

VERSION = 1.0

HOLIDAYS = [
    {'day': 1, 'month': 1, 'description': 'Confraternizacao Universal'},
    {'day': 25, 'month': 1, 'description': 'Aniversario de Sao Paulo'},
    {'day': 3, 'month': 4, 'description': 'Sexta-Feira Santa'},
    {'day': 21, 'month': 4, 'description': 'Tiradentes'},
    {'day': 1, 'month': 5, 'description': 'Dia do Trabalho'},
    {'day': 7, 'month': 9, 'description': 'Independencia do Brasil'},
    {'day': 12, 'month': 10, 'description': 'Nsa. Sra. Aparecida'},
    {'day': 2, 'month': 11, 'description': 'Finados'},
    {'day': 25, 'month': 12, 'description': 'Natal'},
]


def import_mssql_connector():
    """
    Tenta importar conector para conexão com Microsoft SQL Server.
    Caso pacote não exista instala dependências e o conector.
    """

    try:
        global pymssql, tabulate
        import pymssql, tabulate
    except ImportError:
        install_dependencies()


def install_dependencies():
    """
    Instala dependências.
    """

    print('INICIANDO INSTALAÇÃO DE DEPENDÊNCIAS...')

    if os.getuid() != 0:
        print('Operação não permitida! Execute novamente com sudo.')
        sys.exit()

    os.system('apt-get install python-dev')
    os.system('apt-get install freetds-dev')

    # Instala última versão do pip.
    # O pacote python-pip do repositório Ubuntu/Mint Xfce, instalado via apt-get,
    # tá quebrado. Ao instalar certos pacote via pip o mesmo não compila.
    os.system('wget -nv -O- https://bootstrap.pypa.io/get-pip.py | python -c "import sys; exec(sys.stdin.read())"')

    # Instala conector e módulo para tabulação dos resultados.
    os.system('pip install pymssql')
    os.system('pip install tabulate')

    # Tenta importar novamente... loop ∞ ?
    import_mssql_connector()


def show_movements():
    """
    Exibe movimentações.
    """
    connection = get_db_connection()
    cursor = connection.cursor()

    # Argumentos passados via linha de comando
    args = get_args()
    validate_args(args)

    query = get_query(args.credential, args.month, args.year)
    cursor.execute(query)
    rows = cursor.fetchall()
    connection.close()

    # Funcionário
    employee_name = rows[0][2] if len(rows) > 0 else ""

    table = []
    month_consolidated_hours = timedelta()

    for row in rows:
        row = format_row(row)
        month_consolidated_hours += row['consolidated_hours']

        table.append([
            row['formatted_day'],
            row['formatted_entry_time'],
            row['formatted_exit_time'],
            row['formatted_consolidated_hours']
        ])



    headers = ['DIA', 'ENTRADA', 'SAIDA', 'HORAS CONSOLIDADAS']

    # Horas previstas
    foreseen_hours = get_business_days_quantity(datetime.now().strftime('%d')) * 8

    # Horas consolidadas
    hours = month_consolidated_hours.seconds / 3600
    minutes = (month_consolidated_hours.seconds - (hours * 3600)) / 60
    hours += month_consolidated_hours.days * 24

    foreseen = ['', '', 'PREVISTO', "{0}h".format(foreseen_hours)]
    consolidated = ['', '', 'CONSOLIDADO', "{0}h{1:02d}".format(hours, minutes)]

    table.append(['', '', '', ''])
    table.append(foreseen)
    table.append(consolidated)

    print("\nNOME: {0}".format(employee_name.encode('utf-8')))
    print("HORAS ÚTEIS: {0}h\n\n".format(get_business_days_quantity() * 8))

    # Exibe entradas e saidas
    print(tabulate.tabulate(table, headers, tablefmt="orgtbl") + "\n\n")

    # Exibe feriados do mês caso existam.
    show_holidays()


def get_args():
    """
    Retorna argumentos e valor informados pelo usuário na execução.
    """

    current_month = datetime.now().strftime("%m")
    current_year = datetime.now().strftime("%Y")

    # Parse de argumentos passados via linha de comando.
    global parser
    parser = argparse.ArgumentParser(description='DIMEP')

    parser.add_argument(
        '-c', dest='credential',
        type=int,
        help='Número da credencial impressa no crachá'
    )
    parser.add_argument(
        '-m',
        dest='month',
        type=int,
        default=current_month,
        help='Número do mês (padrão: mês atual)'
    )
    parser.add_argument(
        '-y',
        dest='year',
        type=int,
        default=current_year,
        help='Ano (padrão: ano atual)'
    )

    return parser.parse_args()


def validate_args(args):
    """
    Valida argumentos.
    """

    if args.credential is None:
        print('Infome sua credencial')
        parser.print_help()
        sys.exit()

    if args.month not in range(1,13):
        print('Mês inválido')
        parser.print_help()
        sys.exit()


def get_db_connection():
    """
    Retorna conexão com banco de dados.
    """

    HOST = ''
    DATABASE = ''
    USER = ''
    PASSWORD = ''

    try:
        return pymssql.connect(HOST, USER, PASSWORD, DATABASE)
    except:
        print('Informe os dados de conexão com o banco em get_db_connection().')
        sys.exit()


def get_query(credential, month, year):
    """
    Retorna query.
    """
    # TODO: performance zero aqui.
    # Rescrever query agrupando por entrada, saida desconsiderando dia.
    # Dessa forma deverá resolver o problema de entrada em um dia e saída no
    # próximo.
    query = """
        SELECT
            entry_time,
            exit_time,
            pes_nome AS employee_name

        FROM
            ((
                SELECT MIN( mov_datahora ) AS entry_time
                FROM log_credencial
                WHERE
                    mov_entradasaida = 1
                    AND pes_numero = {0}
                    AND DATEPART(MONTH, mov_datahora) = '{1}'
                    AND DATEPART(YEAR, mov_datahora) = '{2}'
                GROUP BY
                    CAST( mov_datahora AS DATE )
            ) i

            FULL OUTER JOIN

            (
                SELECT MAX( mov_datahora ) AS exit_time
                FROM log_credencial
                WHERE
                    mov_entradasaida = 2
                    AND pes_numero = {0}
                    AND DATEPART(MONTH, mov_datahora) = '{1}'
                    AND DATEPART(YEAR, mov_datahora) = '{2}'
                GROUP BY
                    CAST( mov_datahora AS DATE )
            ) o

            ON CAST( i.entry_time AS DATE ) = CAST( o.exit_time AS DATE )),
            pessoas p WHERE p.pes_numero = {0}
    """.format(credential, month, year)
    return query


def format_row(row):
    """
    Formata linha para exibição.
    """

    entry_time = row[0]
    exit_time = row[1]
    consolidated_hours = timedelta()

    formatted_day = "" if entry_time is None else entry_time.strftime("%d/%m/%Y")
    formatted_entry_time = "" if entry_time is None else entry_time.strftime("%Hh%M")
    formatted_exit_time = ""
    formatted_consolidated_hours = ""

    if exit_time is not None and exit_time.date() != date.today():
        formatted_exit_time = exit_time.strftime("%Hh%M")

    if entry_time is not None and (exit_time is None or exit_time.date() == date.today()):
        consolidated_hours = datetime.now() - entry_time

    if entry_time is not None and exit_time is not None and exit_time.date() != date.today():
        consolidated_hours = exit_time - entry_time

    if consolidated_hours > timedelta(hours=4):
        consolidated_hours = consolidated_hours - timedelta(hours=1)

    # Horas extras só são contabilizadas a partir de 8h e 11 minutos trabalhados.
    if consolidated_hours > timedelta(hours=8) and consolidated_hours < timedelta(hours=8, minutes=11):
        consolidated_hours = timedelta(hours=8)

    hours = consolidated_hours.seconds / 3600
    minutes = (consolidated_hours.seconds - (hours * 3600)) / 60
    hours += consolidated_hours.days * 24
    formatted_consolidated_hours = "{0}h{1:02d}".format(hours, minutes)

    return {
        'formatted_day': formatted_day,
        'formatted_entry_time': formatted_entry_time,
        'formatted_exit_time': formatted_exit_time,
        'formatted_consolidated_hours': formatted_consolidated_hours,
        'consolidated_hours': consolidated_hours,
    }


def get_business_days_quantity(limit_day = 31):
    """
    Retorna quatidade de dias úteis no mês.
    """
    args = get_args()
    businessdays = 0
    calendar = Calendar()

    for week in calendar.monthdayscalendar(args.year, args.month):
        for i, day in enumerate(week):

            if day == 0 or i >= 5:
                continue

            for holiday in HOLIDAYS:
                if holiday['month'] == args.month and holiday['day'] == day:
                    businessdays -= 1
                    continue

            businessdays += 1

            if (int(day) == int(limit_day)):
                return businessdays

    return businessdays


def show_holidays():
    """
    Exibe feriados do mês.
    """
    args = get_args()
    month_holidays = []

    for holiday in HOLIDAYS:
        if holiday['month'] != args.month:
            continue

        month_holidays.append(["{0:02d}/{1} - {2}\n".format(holiday['day'], holiday['month'], holiday['description'])])

    if month_holidays:
        pass
        print(tabulate.tabulate(month_holidays, ['FERIADOS'], tablefmt="orgtbl") + '\n')



import_mssql_connector()
show_movements()
