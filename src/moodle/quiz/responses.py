"""Processa o relatório de respostas de um questionário.

Para obter o arquivo:
    1. Acesse o relatório via:
        Questionário > Configurações (engrenagem) > Respostas
    2. Selecione o grupo desejado, se for o caso.
    3. Selecione as 'Tentativas que estão' 'Finalizada'.
    4. Mostre apenas 'resposta' e 'resposta correta'.
    5. Mostre o relatório.
    6. Faça download do arquivo no formato JSON (UTF-8 .json).
"""

from argparse import ArgumentParser
import os


def read(file, quiz):
    """Lê os dados do arquivo e os retorna como um dicionário.

    O valor definido pela chave quiz é um dicionário cujas chaves são índices
    das questões no questionário e os valores outro dicionário com duas chaves:
    'attempt' que define a resposta do discente e 'answer' que define a
    resposta correta.

    Argumentos:
    file -- o arquivo JSON a ser lido.
    quiz -- o nome do questionário.
    """
    responses = {}
    with open(file) as f:
        import json
        data = json.load(f)

    for d in data[0]:
        s_id, _ = d[2].split('@')  # e-mail
        responses[s_id] = {'Name': f'{d[1]} {d[0]}',
                           quiz: {str(q + 1): {'attempt': d[i].strip(' \r\n'),
                                               'answer': d[i + 1].strip(' \r\n')}
                                  for q, i in enumerate(range(8, len(d), 2))}}
    return responses


def write(responses, output_path, ext='py', ignore=[], header_extra={}):
    """Grava a resposta de um aluno para cada questão em um arquivo específico.

    Cria uma estrutura de diretórios criada para armazenar os arquivos que
    segue as hierarquia das chaves do dicionário de respostas:
        output_path > Nome do Questionário > Questão

    Retorna uma lista com os diretórios (um por questão) onde os arquivos são
    gravados.

    Sendo fornecida a informação, inclui turma do aluno e nota da questão no
    cabeçalho do arquivo.

    Argumentos:
    responses -- dicionario com a informação das respostas (veja a função read).
    output_path -- diretório para armazenar os arquivos.
    ext -- extensão do arquivo a conter a resposta.
    ignore -- lista com índices de questões que devem ser ignoradas.
    header_extra -- dicionário no formato {student_id: {quiz: {questions: [info1, info2, ...]}}} com
                    informações a serem acrescentadas ao final do cabeçalho do
                    arquivo de resposta da questão.
    """
    def has_response(content):
        return content.count('\n') > 1

    def make_header(student_info, ext):
        if ext == 'py':
            return '\n'.join(f'# {i}' for i in student_info)

        if ext in ['c', 'cpp']:
            cmt = '\n   '.join(student_info)
            return f'/* {cmt} */'

        return ' '.join(student_info)

    all_output_paths = set()
    for s_id, info in responses.items():
        for key in info:
            if key == 'Name':
                continue

            for q, src in info[key].items():
                student = ([info['Name'], s_id] +
                           header_extra.get(s_id, {}).get(key, {}).get(q, []))

                if (q not in ignore and has_response(src.get('attempt', ''))):
                    q_dir = os.path.join(output_path, key, f'Q{q}')
                    os.makedirs(q_dir, exist_ok=True)
                    response_file = os.path.join(q_dir, f'{s_id}.{ext}')
                    with open(response_file, 'w') as f:
                        f.write(f'{make_header(student, ext)}'
                                f'\n\n{src["attempt"]}')

                    response_file = os.path.join(q_dir, f'CORRECT.{ext}')
                    if not os.path.isfile(response_file):
                        with open(response_file, 'w') as f:
                            f.write(src['answer'])

                    all_output_paths.add(q_dir)
    return all_output_paths


def main():
    """Processa argumentos da linha de comando."""

    def parse_read(args):
        import locale

        locale.setlocale(locale.LC_ALL, '')
        responses = read(args.file, ' '.join(args.quiz))
        for s_id, info in sorted(responses.items(),
                                 key=lambda x: locale.strxfrm(x[1]['Name'])):
            quizzes = ', '.join(key for key in info if key != 'Name')
            print(f'{info["Name"]} ({s_id}): {quizzes}')

    def parse_write(args):
        responses = read(args.file, args.quiz)
        for path in write(responses, args.output_path, args.ext, args.ignore):
            print(path)

    parser = ArgumentParser(read.__doc__.split('\n')[0])
    parser.add_argument('file', help='O arquivo JSON a ser lido.')
    parser.add_argument('-q', '--quiz', nargs='+', default=['Questionário'],
                        help='O nome do questionário.')
    parser.set_defaults(func=parse_read)

    subparsers = parser.add_subparsers(help='Opções de comandos.')
    write_parser = subparsers.add_parser('write',
                                         help=write.__doc__.split('\n')[0])
    write_parser.add_argument('output_path',
                              help='Diretório para armazenar os arquivos.')
    write_parser.add_argument('ext',
                              help='extensão do arquivo a conter a resposta.')
    write_parser.add_argument('ignore', type=int, nargs='+',
                              help='Índices de questões que devem ser '
                                   'ignoradas.')
    write_parser.set_defaults(func=parse_write)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
