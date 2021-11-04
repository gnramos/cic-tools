"""Processa o relatório de participação discente no curso.

Acrescenta a chave 'Group' que indica os grupos (turma) do discente.

Para obter o arquivo:
    1. Acesse o relatório via:
        Este Curso > Pessoas
    2. Aperte o botão "Selecionar todos os X usuários".
    3. Salve a página como HTML (completo).

Apenas o arquivo HTML é necessário.
"""

import re


def read(file, group='', role='Estudante'):
    """Lê os dados do arquivo e os retorna como um dicionário.

    Argumentos:
    file -- o arquivo HTML a ser lido.
    group -- nome [parcial] do grupo desejado.
    role -- papel [parcial] definido.
            (default Estudante)
    """
    with open(file) as htmlfile:
        html = htmlfile.read()

    pattern = re.compile(r'<label for=.*?user\d+.*?<img.*?>(.*?)</a>.*?'
                         r'>([\d\w]*?)@(aluno\.)?unb\.br[.\s\S]*?'
                         r'"Atribuições de papéis.*?>[\s\S] *(\w.*)[\s\S]'
                         r'[.\s\S]*?'
                         r'"Editar grupos.*?>[\s\S] *(\w.*)[\s\S]')
    return {s_id: {'Name': name, 'Role': s_role, 'Group': s_group}
            for name, s_id, is_aluno, s_role, s_group in pattern.findall(html)
            if group in s_group and role in s_role}


def main():
    """Processa argumentos da linha de comando."""

    from argparse import ArgumentParser

    parser = ArgumentParser(read.__doc__.split('\n')[0])
    parser.add_argument('file', help='O arquivo HTML a ser lido.')
    parser.add_argument('-g', '--group', default='',
                        help='Nome [parcial] do grupo desejado.')
    parser.add_argument('-r', '--role', default='',
                        help='Nome [parcial] do papel desejado.')

    args = parser.parse_args()
    participants = read(args.file, args.group, args.role)

    import locale

    locale.setlocale(locale.LC_ALL, '')
    for info in sorted(participants.values(),
                       key=lambda x: locale.strxfrm(x['Name'])):
        print(f'{info["Name"]}: {info["Group"]} ({info["Role"]})')


if __name__ == '__main__':
    main()
