"""Utilidades relacionadas ao uso do MOSS.

MOSS é uma ferramenta de avaliação de similaridade de código. Assume-se que o
script para solicitação de análise está disponível na máquina. Mais detalhes em
https://theory.stanford.edu/~aiken/moss/ .
"""

from collections import defaultdict
import os
import re


def call(shell_options, path='.', ext='py'):
    """Chama o script moss e retorna a url resultante, se for bem sucedido.

    As opções devem, obrigatoriamente, definir os arquivos a serem avaliados.

    Argumentos:
    shell_options -- opções a serem fornecidas ao script.
    path -- diretório onde estão os arquivos para serem analisados
            (default '.')
    ext -- extensão do tipo de arquivo a ser analisado
           (default 'py')
    """

    import subprocess

    working_dir = os.getcwd()
    os.chdir(path)
    try:
        shell_cmd = ' '.join(['moss'] + shell_options + [f'*.{ext}'])
        cp = subprocess.run(shell_cmd, shell=True, stdout=subprocess.PIPE)

        url = cp.stdout.decode().split('\n')[-2]
    except Exception:
        url = ''
    finally:
        os.chdir(working_dir)

    return url if url.startswith('http') else None


def get_report(url, out_file):
    """Obtém o relatório MOSS da url e salva em um arquivo.

    Retorna um booleano indicando se foi bem sucedido ou não.

    Argumentos:
    url -- url do relatório MOSS.
    out_file -- nome do arquivo onde salvar o relatório.
    """

    import urllib.request

    try:
        with urllib.request.urlopen(url) as response:
            html = response.read().decode('utf-8')

        with open(out_file, 'w', encoding='utf-8') as f:
            f.writelines(html.replace('Moss Results', f'Moss Results - {url}'))
        return True
    except urllib.error.HTTPError as e:
        print(e)

    return False


def similar(moss_report, threshold=30):
    """Lê um relatório gerado pelo MOSS e agrupa os arquivos similares.

    Retorna uma lista com grupos de submissões similares, conforme o limiar.
    Assume que cada arquivo tem um nome único, independentemente do caminho até
    ele.

    Argumentos:
    -- moss_report: caminho para o arquivo HTML com o relatório MOSS.
    -- threshold: o limiar de similaridade percentual.
    """
    def file_name(moss_report):
        _, tail = os.path.split(moss_report)
        name, _ = os.path.splitext(tail)
        return name

    if not os.path.isfile(moss_report):
        return []

    with open(moss_report, 'r') as f:
        moss_html = f.read()

    pattern = r'<TR><TD><A HREF=".*?">(.*?) \((\d\d)%\)</A>[.\s\S]*?' \
              r'A HREF=".*?">(.*?) \((\d\d)%\)'
    similar_files = defaultdict(list)
    for file1, p1, file2, p2 in re.findall(pattern, moss_html, re.IGNORECASE):
        if int(p1) >= threshold or int(p2) >= threshold:
            file1, file2 = file_name(file1), file_name(file2)
            similar_files[file1].append(file2)
            similar_files[file2].append(file1)

    similar_groups = []
    for k, v in similar_files.items():
        if (s := set([k] + v)) not in similar_groups:
            similar_groups.append(s)

    return similar_groups


def main():
    """Processa argumentos da linha de comando."""

    def parse_report(args):
        if get_report(args.url, args.out_file):
            print(f'Relatório armazenado em {args.out_file}.')
        else:
            print(f'Houve um problema obtendo o relatório de {args.url}.')

    def parse_similar(args):
        groups = similar(args.report, args.threshold)
        for i, group in enumerate(groups):
            print(f'Grupo {i + 1}): ' + ', '.join(sorted(group)))

    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers(help='Opções de comandos.')
    report_parser = subparsers.add_parser('report',
                                          help=get_report.__doc__.split(
                                            '\n')[0])
    report_parser.add_argument('url', help='url do relatório MOSS.')
    report_parser.add_argument('out_file', help='Caminho para o arquivo onde '
                                                'salvar o relatório')
    report_parser.set_defaults(func=parse_report)
    similar_parser = subparsers.add_parser('similar',
                                           help=similar.__doc__.split('\n')[0])
    similar_parser.add_argument('report',
                                help='Caminho para o arquivo HTML com o '
                                'relatório MOSS.')
    similar_parser.add_argument('-t', '--threshold', type=int, default=30,
                                help='Limiar de similaridade percentual.')
    similar_parser.set_defaults(func=parse_similar)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
