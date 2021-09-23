import re
import xml.etree.ElementTree as ET


#######################################################################
def _CDATA(text=None):
    # text = re.sub(r']]>', r']]&gt;', text)
    element = ET.Element('![CDATA[')
    element.text = text
    return element


ET._original_serialize_xml = ET._serialize_xml


def _serialize_xml(write, elem, qnames, namespaces, short_empty_elements,
                   **kwargs):
    if elem.tag == '![CDATA[':
        write(f'<{elem.tag}{elem.text}]]>')
        if elem.tail:
            write(ET._escape_cdata(elem.tail))
    else:
        return ET._original_serialize_xml(write, elem, qnames, namespaces,
                                          short_empty_elements, **kwargs)


ET._serialize_xml = ET._serialize['xml'] = _serialize_xml
#######################################################################


"""Checks (and updates) questions according to expected values.

Uses a specific static method per setting, if available.
"""

DEFAULT_EMPTY = "This should have no value!"
DEFAULT_NOT_EMPTY = "This must have a value!"
UNFIXABLE = ['answer', 'tags', 'template', 'testcases']
DEFAULTS = {  # setting: list of values
    'allornothing': ['0'],
    'answer': [''],  # necessário
    'coderunnertype': ['python3_try_except'],
    'cputimelimitsecs': ['', DEFAULT_EMPTY],
    'defaultgrade': ['1.0000000', '1'],
    'displayfeedback': ['0'],  # [Set by quiz, Force Show, Force hide]
    'generalfeedback': [''],  # necessário
    'memlimitmb': ['', DEFAULT_EMPTY],
    'penaltyregime': ['0, 0, 10, 20, ...'],
    'precheck': ['2'],  # [Disabled, Empty, Examples, Selected, All]
    'validateonsave': ['1'],
    'testcases': {'example': ('1', '0.0010000', 'SHOW', 3),
                  'visible': ('0', '1.0000000', 'SHOW', 3),
                  'hidden': ('0', '1.0000000', 'HIDE', 4)}
    }


def _add_CDATA(question):
    # Tags with possible special characters
    # for element in question.findall('.//*[@format="html"]'):
    html_fragments = ('generalfeedback/text', 'questiontext/text')
    for tag in html_fragments:
        element = question.find(tag)
        if element is not None and element.text and element.text.strip():
            text = _clean_html(element.text.strip())
            element.clear()
            element.append(_CDATA(text))


# # _check_SETTING methods
def _check_default(question, setting, values=[]):
    """Checks the question for the given setting.

    If values are given, setting cannot be empty.
    """
    element = question.find(f'{setting}/text')
    if element is None:
        element = question.find(f'{setting}')
    if element is not None and (text := element.text):
        if values and text not in values and values[0]:
            return f'é "{text}" (deveria ser "{values[0]}")'
    elif values:
        if DEFAULT_EMPTY not in values:
            return 'ausente'


def _check_displayfeedback(question, values):
    if issues := _check_default(question, 'displayfeedback', values):
        # Replace number with text
        options = ('Set by quiz', 'Force Show', 'Force hide')
        parts = issues.split('"')
        parts[1], parts[3] = options[int(parts[1])], options[int(parts[3])]
        return '"'.join(parts)


def _check_precheck(question, values):
    if issues := _check_default(question, 'precheck', values):
        # Replace number with text
        options = ('Disabled', 'Empty', 'Examples', 'Selected', 'All')
        parts = issues.split('"')
        parts[1], parts[3] = options[int(parts[1])], options[int(parts[3])]
        return '"'.join(parts)


def _check_questiontext(question, values):
    questiontext = question.find('questiontext/text').text

    if values and questiontext not in values:
        return f'é "{questiontext}" (deveria estar em "{values}")'

    name = question.find('name/text').text
    issues = ''
    if f'<h3>{name}</h3>' not in questiontext:
        issues = 'não apresenta título no formato previsto'
    if '<span' in questiontext:
        if issues:
            issues = f'{issues} e '
        issues = f'{issues}tem tag <span>'
    return issues


def _check_setting(question, setting, values):
    if f'_check_{setting}' in globals():
        if issues := eval(f'_check_{setting}(question, values)'):
            return f'[{setting}] {issues}'
    elif issues := _check_default(question, setting, values):
        return f'[{setting}] {issues}'


def _check_tags(question, value):
    tags = [test.text for test in question.findall('tags/tag/text')]
    if value:
        if isinstance(value, list):
            ausentes = [v for v in value if v not in tags]
        else:
            ausentes = '' if value in tags else value
        if ausentes:
            return f'é "{tags}" (deveria conter "{ausentes}")'
    elif num_tags := sum(tag.lower() in ('fácil', 'médio', 'difícil')
                         for tag in tags):
        if num_tags > 1:
            return 'múltiplos níveis de dificuldade'
    else:
        return 'nível de dificuldade ausente'


def _check_template(question, value):
    text = question.find('template').text
    if value and text and value != text:
        return ' tem template de correção'


def _check_testcases(question, value):
    def check(useasexample, mark_value, display_value, num_cases):
        cases = [test for test in question.findall(
            f'testcases/testcase[@useasexample="{useasexample}"]')
            if test.find('display/text').text == display_value]

        issues = ''
        for t, test in enumerate(cases):
            if has_issue := (mark_value != test.attrib['mark']):
                if issues:
                    issues = f'{issues}. '

                issues = (f'Caso {t} tem pontuação '
                          f'{test.attrib["mark"]} '
                          f'(deveria ser {mark_value})')

            display = test.find('display/text').text
            if display != display_value:
                issues = f'{issues} e' if has_issue else f'Caso {t}'
                issues = (f'{issues} tem visibilidade {display} '
                          f'(deveria ser "{display_value}")')

        if len(cases) != num_cases:
            if useasexample == '1':
                test_type = 'exemplos'
            elif display_value == 'SHOW':
                test_type = 'visíveis'
            else:
                test_type = 'escondidos'
            issues = f'{issues} e são' if issues else 'São'
            issues = (f'{issues} {len(cases)} testes {test_type} '
                      f'(deveriam ser {num_cases})')

        return issues

    issues = [check(*value[case])
              for case in ('example', 'visible', 'hidden')]

    return '. '.join(x for x in issues if x)


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
                    # Tentanto eliminar <span> vazios aninhados.
                    (r'(<span>[.\s\S]*?</span>)', replace_empty_span),
                    (r'(<span>[.\s\S]*?</span>)', replace_empty_span))

    for pattern, repl in replacements:
        html = re.sub(pattern, repl, html)

    return html


def _coderunner_questions(file):
    """Iterates through the questions in the given XML file.

    Each item is the tuple (tree, category, question) for the quiz's
    ElementTree and question's category and Element, respectively.
    """

    tree, category = ET.parse(file), None
    for question in tree.getroot():
        # As per Moodle documentation: "Within the <quiz> tags are any
        # number of <question> tags. One of these <question> tags can be a
        # dummy question with a category type to specify a category for the
        # import/export." Thus, all questions following a "category" type
        # belong to that category in the question bank.
        if question.get('type') == 'category':
            category = question.find('category/text').text.replace(
                '$course$/top/', '')
        elif (question.get('type') == 'coderunner' and
              question.find('prototypetype').text == '0'):
            yield tree, category, question


# _fix_SETTING methods
def _fix_default(question, setting, value):
    if value is not None and question.find(setting).text != value:
        question.find(setting).text = value


def _fix_questiontext(question, value=None):
    name = question.find('name/text').text
    questiontext = question.find('questiontext/text')

    # Handle regex characters.
    name = ''.join(f'\\{c}' if c in r'\{[()]}.' else c for c in name)
    pattern = f'<h(\\d)>(.*?)({name})(.*?)</h\\d>'
    if m := re.search(pattern, questiontext.text, flags=re.IGNORECASE):
        if m.groups() != ('3', '', name, ''):
            questiontext.text = re.sub(pattern, '', questiontext.text,
                                       flags=re.IGNORECASE)
    questiontext.text = f'<h3>{name}</h3>\n{questiontext.text.lstrip()}'


def _fix_setting(category, question, setting, value, sep=' > '):
    if setting in UNFIXABLE:
        return f'Não é possível ajustar "{setting}"!'

    if f'_fix_{setting}' in globals():
        exec(f'_fix_{setting}(question, value)')
    else:
        _fix_default(question, setting, value)

    return ''


def _print_dict(d, indent_level=0):
    for k, v in d.items():
        if isinstance(v, dict):
            print(f'{indent_level * "    "} - {k}:')
            _print_dict(v, indent_level + 1)
        else:
            print(f'{indent_level * "    "} - {k}: {v}')


def check(file, values, outfile=None, set_values=False,
          yes_to_all=False, ignore_list=[], sep=' > '):
    """Checks all questions in quiz file with the given setting values.

    Returns a boolean indicating if no issue was found. Also prints any
    found issues (identifying the question).

    Args:
      - file: XML file with quiz/question info.
      - values: dict in the {setting: value} format.
      - outfile: string with the file to write the validated quiz to.
                 (default: same as file)
      - set_values: boolean indicating whether to replace the non-default
                      values with the default ones.
                      (default: False)
      - yes_to_all: boolean indicating whether to prompt user for
                    confirmation for every issue found.
                    (default: False)
      - ignore_list: list fo settings (strings) to ignore.
                    (default: [])
      - sep: string for separating question category levels.
             (default: ' > ')
    """
    if outfile is None:
        from datetime import datetime

        now = datetime.now().strftime('%Y%m%d%H%M%S')
        outfile = f'{file[:-4]}_{now}{file[-4:]}'

    all_valid = True
    for tree, category, question in _coderunner_questions(file):
        name = question.find('name/text').text

        if not question.find('tags'):
            question.append(ET.Element('tags'))

        for child in question:
            setting, value = child.tag, values.get(child.tag, [])
            if setting in ignore_list:
                continue

            issues = _check_setting(question, setting, value)
            if issues:
                all_valid = False
                if category:
                    category = category.replace("/", sep)
                else:
                    category = '[No category]'
                print(f'{category}{sep}{name}: {issues}.')

                if not set_values:
                    continue

                if yes_to_all:
                    fix_value = True
                else:
                    response = input(f'Tentar ajustar o valor de "{setting}"?'
                                     ' [Y/N] ')
                    fix_value = response and response in 'yY'

                if fix_value:
                    if isinstance(value, list) and value:
                        value = value[0]
                    if issue := _fix_setting(category, question, setting,
                                             value, sep):
                        print(f'\t[{setting}] {issue}')
                    else:
                        print(f'\t[{setting}] ajustado!')
                print()

        if set_values:
            _add_CDATA(question)

    if set_values:
        tree.write(outfile, encoding='UTF-8', xml_declaration=True)

    return all_valid


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='Quiz XML file.')
    parser.add_argument('-l', '--list_values', action='store_true',
                        help='List suggested values and exit.')
    parser.add_argument('-s', '--set_values', action='store_true',
                        help='Set values, writing to a new file.')
    parser.add_argument('-o', '--outfile',
                        help='Output file name.')
    parser.add_argument('-y', '--yes_to_all', action='store_true',
                        help='Answer YES to any iteractions.')
    parser.add_argument('-i', '--ignore', nargs='*', default=[],
                        help='Ignore given settings.')
    args = parser.parse_args()

    if args.list_values:
        print('Suggested values:')
        _print_dict(DEFAULTS)
    else:
        check(args.file, DEFAULTS, args.outfile, set_values=args.set_values,
              yes_to_all=args.yes_to_all, ignore_list=args.ignore)
