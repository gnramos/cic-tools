import argparse
import os
import re
import xml.etree.ElementTree as ET


#######################################################################
def _CDATA(content):
    # https://docs.moodle.org/310/en/Moodle_XML_format#A_word_about_validity_.28and_CDATA.29
    # HTML fragments should be within CDATA section
    # content = re.sub(r']]>', r']]&gt;', content).strip()
    element = ET.Element('![CDATA[')
    element.text = content
    return element


# Reference to original function.
_serialize_xml = ET._serialize_xml


def _serialize_xml_with_CDATA(write, elem, qnames, namespaces,
                              short_empty_elements, **kwargs):
    if elem.tag == '![CDATA[':
        write(f'<{elem.tag}{elem.text}]]>\n')
    else:
        return _serialize_xml(write, elem, qnames, namespaces,
                              short_empty_elements, **kwargs)


ET._serialize_xml = ET._serialize['xml'] = _serialize_xml_with_CDATA
#######################################################################


DEFAULTS = {'defaultgrade': ['1.0000000', '1'],
            'allornothing': ['0'],
            'penaltyregime': ['0, 0, 10, 20, ...'],
            'precheck': ['2'],
            'validateonsave': ['1'],
            'testcase': {'example': ('1', '0.0010000', 'SHOW', 3),
                         'visible': ('0', '1.0000000', 'SHOW', 3),
                         'hidden': ('0', '1.0000000', 'HIDE', 4)}
            }


def _add_CDATA(question):
    # Tags with possible special characters
    html_fragments = ('answer', 'answerpreload', 'generalfeedback/text',
                      'questiontext/text', 'template', 'templateparams',
                      'testcases/expected/text', 'testcases/extra/text',
                      'testcases/stdin/text', 'testcases/testcode/text')

    # for element in question.findall('.//*[@format="html"]'):
    for tag in html_fragments:
        element = question.find(tag)
        if element is not None and element.text:
            text = element.text
            element.clear()
            element.append(_CDATA(_clean_html(text)))


def _clean_html(html):
    def replace_empty_span(matchobj):
        return matchobj.group(0)[6:-7]

    replacements = (  # (r'(<(?!\/)[^>]+>)+(<\/[^>]+>)+', ''),
                    (r'( style="font-size: \d+\.\d+rem;"?)', ''),
                    (r'( style="")', ''),
                    (r'(<span>[.\s\S]*?</span>)', replace_empty_span),
                    (r'&nbsp;', ' '),
                    (r'<([^ ]*?)><br></(\1)>', ''),
                    (r'<([^ ]*?)></(\1)>', ''),
                    # Tentanto eliminar <span> vazios aninhados aninhados.
                    (r'(<span>[.\s\S]*?</span>)', replace_empty_span),
                    (r'(<span>[.\s\S]*?</span>)', replace_empty_span))

    for pattern, repl in replacements:
        html = re.sub(pattern, repl, html)

    return html


def _fix_default(question, setting):
    question.find(setting).text = DEFAULTS[setting][0]


def _fix_questiontext(question):
    name = question.find('name/text').text
    questiontext = question.find('questiontext/text')

    # Handle regex characters.
    name = ''.join(f'\\{c}' if c in r'\{[()]}.' else c for c in name)
    pattern = f'<h(\\d)>{name}</h\\d>'
    if m := re.search(pattern, questiontext.text, flags=re.IGNORECASE):
        if m.group(1) != '3':
            questiontext.text = re.sub(f'<h(\\d)>{name}</h\\d>',
                                       f'<h3>{name}</h3>',
                                       questiontext.text)
    else:
        questiontext.text = f'<h3>{name}</h3>\n{questiontext.text}'


def _fix_coderunnertype(question):
    if question.find('template') is None:
        question.find('coderunnertype').text = 'python3_try_except'


def _fix(question, setting):
    if fix := globals().get(f'fix_{setting}', None):
        print(f'Ajustando {setting}.')
        fix(question)
    elif setting in DEFAULTS:
        print(f'Ajustando {setting}.')
        _fix_default(question, setting)
    else:
        print(f'Não sei ajustar {setting}.')


def _check_default(question, setting):
    text = question.find(setting).text
    if text in DEFAULTS[setting]:
        return None
    return f'é {text} (deveria ser {DEFAULTS[setting][0]})'


def _check_questiontext(question):
    name = question.find('name/text').text
    questiontext = question.find('questiontext/text').text
    issues = ''
    if f'<h3>{name}</h3>' not in questiontext:
        issues = 'não apresenta título'
    if '<span' in questiontext:
        if issues:
            issues = f'{issues} e '
        issues = f'{issues}tem tag <span>'
    return issues


def _check_generalfeedback(question):
    return None if question.find('generalfeedback/text').text else 'ausente'


def _check_answer(question):
    return None if question.find('answer').text else 'ausente'


def _check_coderunnertype(question):
    coderunnertype = question.find('coderunnertype').text
    issues = None
    if coderunnertype != 'python3_try_except':
        issues = f'tipo de questão é {coderunnertype}'
    if question.find('template'):
        if issues:
            issues = f'{issues} e '
        issues = f'{issues}já tem template de correção'
    return issues


def _check_tags(question):
    tags = [test.text for test in question.findall('tags/tag/text')]
    if sum(tag.lower() in ('fácil', 'médio', 'difícil') for tag in tags) != 1:
        return 'nível de dificuldade ausente/incorreto'


def _check_testcases(question):
    def check(useasexample, mark_value, display_value, num_cases):
        cases = [test for test in question.findall(
            f'testcases/testcase[@useasexample="{useasexample}"]')
                 if test.find('display/text').text == display_value]

        issues = ''
        for t, test in enumerate(cases):
            if has_issue := (mark_value != test.attrib['mark']):
                if issues:
                    issues = f'{issues}. '

                issues = f'Caso {t} tem pontuação {test.attrib["mark"]} ' \
                         f'(deveria ser {mark_value})'

            display = test.find('display/text').text
            if display != display_value:
                issues = f'{issues} e' if has_issue else f'Caso {t}'
                issues = f'{issues} tem visibilidade {display} (deveria ser ' \
                         f'"{display_value}")'

        if len(cases) != num_cases:
            type = ('exemplos'
                    if useasexample == '1'
                    else 'visíveis' if display_value == "SHOW"
                    else 'escondidos')
            issues = f'{issues} e são' if issues else 'São'
            issues = f'{issues} {len(cases)} testes {type} (deveriam ser ' \
                     f'{num_cases})'

        return issues

    issues = '. '.join(check(*DEFAULTS['testcase'][case])
                       for case in ('example', 'visible', 'hidden'))

    return issues


def _check(question, setting):
    issues = None
    if check := globals().get(f'_check_{setting}', None):
        if issues := check(question):
            return f'[{setting}] {issues}'
    elif setting in DEFAULTS:
        if issues := _check_default(question, setting):
            return f'[{setting}] {issues}'

    return issues


#######################################################################
def _argparser():
    def check_file(file):
        if not os.path.isfile(file):
            raise argparse.ArgumentTypeError(f'{file} does not exist')

        _, ext = os.path.splitext(file)
        if ext.lower() != '.xml':
            raise argparse.ArgumentTypeError(f'{file} is not XML')

        return file

    parser = argparse.ArgumentParser(
        description="Processes a question bank's XML file and "
                    "verifies question formatting.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''To get the XML file:
1. Access the question bank via the Course Admin page:
   Moodle > Course > Cog (Settings) > Question Bank > Export.
2. Select the "Moodle XML" option.
3. Select the top category.
4. Mark all options.
5. Export to file.''')

    parser.add_argument('file', type=check_file,
                        help='file with question bank data')
    parser.add_argument('-o', '--outfile', help='output file in case of '
                        'updating default values')
    parser.add_argument('--set_default', action='store_true',
                        help='reconfigure non default settings to the default '
                             'values.')

    return parser


if __name__ == '__main__':
    parser = _argparser()
    args = parser.parse_args()

    if args.outfile and args.set_default is None:
        print('Ignoring output file "{args.outfile}".')

    tree = ET.parse(args.file)
    root = tree.getroot()

    last_category = current_category = None
    # Within the <quiz> tags are any number of <question> tags. One of these
    # <question> tags can be a dummy question with a category type to specify a
    # category for the import/export.
    #
    # As questões subsequentes à questão de tipo "categoria" pertencem a essa
    # categoria
    for question in root:
        this_type = question.get('type')
        if this_type == 'category':
            last_category = current_category
            current_category = question.find('category/text').text.replace('$course$/top/', '')
        elif this_type == 'coderunner' and question.find('prototypetype').text == '0':
            if not question.find('tags'):
                question.append(ET.Element('tags'))

            name = question.find('name/text').text
            for child in question:
                if issues := _check(question, child.tag):
                    print(f'{current_category} > "{name}": {issues}.')

                    if args.set_default:
                        _fix(question, child.tag)

            _add_CDATA(question)

    if args.set_default:
        if args.outfile is None:
            root_path, ext = os.path.splitext(args.file)
            args.outfile = f'{root_path}_OUT{ext}'

        tree.write(args.outfile, encoding='UTF-8', xml_declaration=True)
