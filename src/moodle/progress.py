"""Processa o relatório de progresso de discentes no curso.

Acrescenta "Frequência" e "Faltas" do discente, em termos percentuais.

Para obter o arquivo:
    1. Acesse o relatório via:
        Administração do curso > Relatórios (aba) > Conclusão de atividades
    2. Selecione o grupo desejado, se for o caso.
    3. Faça o download em formato de planilha (UTF-8. csv).
"""

import csv


def read(file, info):
    """Lê os dados do arquivo e os retorna como um dicionário.

    Argumentos:
    file -- o arquivo CSV a ser lido.
    info -- string descrevendo o arquivo.
    """
    progress = {}
    with open(file) as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')

        header = next(csvreader)  # skip header
        activities = (len(header) - 2) / 2

        for row in csvreader:
            s_id, _ = row[1].split('@')
            frequency = 100 * row.count('Concluído') // activities
            progress[s_id] = {'Name': row[0],
                              'Frequência': frequency,
                              'Faltas': 100 - frequency}
    return progress


def main():
    """Processa argumentos da linha de comando."""

    from argparse import ArgumentParser
    import locale

    parser = ArgumentParser(read.__doc__.split('\n')[0])
    parser.add_argument('file', help='O arquivo CSV a ser lido.')

    args = parser.parse_args()
    progress = read(args.file, None)

    locale.setlocale(locale.LC_ALL, '')
    for info in sorted(progress.values(),
                       key=lambda x: locale.strxfrm(x['Name']).lower()):
        print(f'{info["Name"]}, Frequência: {info["Frequência"]}, '
              f'Faltas: {info["Faltas"]}')


if __name__ == '__main__':
    main()
