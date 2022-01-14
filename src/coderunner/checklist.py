"""Batch analysis for CodeRunner question type settings.

Details in: https://github.com/trampgeek/moodle-qtype_coderunner
"""

import re
import xml.etree.ElementTree as ET


#######################################################################
# Override CDATA serialization for HTML.
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
UNFIXABLE = ['answer', 'tags', 'template', 'testcases']
DEFAULTS = {  # setting: list of values
    'allornothing': ['0'],
    'answer': [''],  # required
    'coderunnertype': ['python3_try_except'],
    'cputimelimitsecs': ['', DEFAULT_EMPTY],
    'defaultgrade': ['1.0000000', '1'],
    'displayfeedback': ['0'],  # [SET BY QUIZ, Force hide]
    'generalfeedback': [''],  # required
    'memlimitmb': ['', DEFAULT_EMPTY],
    'penaltyregime': ['0, 0, 10, 20, ...'],
    'precheck': ['2'],  # [Disabled, Empty, EXAMPLES, Selected, All]
    'validateonsave': ['1'],
    'testcases': {'example': ('1', '0.0010000', 'SHOW', 3),
                  'visible': ('0', '1.0000000', 'SHOW', 3),
                  'hidden': ('0', '1.0000000', 'HIDE', 4)}
    }


def _add_CDATA(question, html_fragments=('generalfeedback/text',
                                         'questiontext/text')):
    # Tags with possible special characters
    # for element in question.findall('.//*[@format="html"]'):
    for tag in html_fragments:
        element = question.find(tag)
        if element is not None and element.text and element.text.strip():
            text = _clean_html(element.text.strip())
            element.clear()
            element.append(_CDATA(text))


# _check_SETTING methods
def _check_default(question, setting, values=[]):
    """Checks the question for the given setting.

    If values are given, setting cannot be empty.
    """
    element = question.find(f'{setting}/text')
    if element is None:
        element = question.find(f'{setting}')
    if element is not None and (text := element.text):
        if values and text not in values and values[0]:
            return f'value is "{text}" (should be "{values[0]}")'
    elif values:
        if DEFAULT_EMPTY not in values:
            return 'missing'


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
    # questiontext should start with the question name as its title and between
    # <h3> tags. <span> tags should not exist.
    questiontext = question.find('questiontext/text').text

    if values and questiontext not in values:
        return f'value is "{questiontext}" (should be in "{values}")'

    name = question.find('name/text').text
    issues = ''
    if f'<h3>{name}</h3>' not in questiontext:
        issues = 'title format is incorrect'
    if '<span' in questiontext:
        if issues:
            issues = f'{issues} and '
        issues = f'{issues}has tag <span>'
    return issues


def _check_setting(question, setting, values):
    if f'_check_{setting}' in globals():
        if issues := eval(f'_check_{setting}(question, values)'):
            return f'[{setting}] {issues}'
    elif issues := _check_default(question, setting, values):
        return f'[{setting}] {issues}'


def _check_tags(question, value, expected_tags=('fácil', 'médio', 'difícil')):
    tags = [test.text for test in question.findall('tags/tag/text')]
    if value:
        if isinstance(value, list):
            ausentes = [v for v in value if v not in tags]
        else:
            ausentes = '' if value in tags else value
        if ausentes:
            return f'value is "{tags}" (should have "{ausentes}")'
    elif num_tags := sum(tag.lower() in expected_tags
                         for tag in tags):
        if num_tags > 1:
            return 'multiple difficulty levels'
    else:
        return 'difficulty level missing'


def _check_template(question, value):
    text = question.find('template').text
    if value and text and value != text:
        return ' has a template'


def _check_testcases(question, value):
    def get_type(test):
        if test.find('display/text').text == 'HIDE':
            return 'hidden'
        if test.attrib['useasexample'] == '1':
            return 'example'
        return 'visible'

    def check(t, test, useasexample, mark, display, num_cases):
        issue = ''
        if mark != test.attrib['mark']:
            issue = (f'{issue}Test case {t} mark is {test.attrib["mark"]} '
                     f'(should be {mark})')

        if (d := test.find('display/text').text) != display:
            issue = f'{issue} and' if issue else f'Test case {t}'
            issue = (f'{issue} visibility is {d} '
                     f'(should be "{display}")')

        return issue

    counter, issues = {'example': 0, 'visible': 0, 'hidden': 0}, []
    for t, test in enumerate(question.findall('testcases/testcase')):
        test_type = get_type(test)
        counter[test_type] += 1

        if issue := check(t + 1, test, *value[test_type]):
            issues.append(issue)

    for test_type, count in counter.items():
        if count != value[test_type][-1]:
            issues.append(f'There are {count} {test_type} tests '
                          f'(should be {value[test_type][-1]})')

    return '. '.join(issue for issue in issues)


def _clean_html(html):
    def remove_span_tag(matchobj):
        return matchobj.group(0)[6:-7]  # chars between <span> and </span>

    replacements = ((r'( style="font-size: \d+\.\d+rem;"?)', ''),
                    (r'( style="")', ''),
                    (r'(<span>[.\s\S]*?</span>)', remove_span_tag),
                    (r'&nbsp;', ' '),
                    (r'<([^ ]*?)><br></(\1)>', ''),
                    (r'<([^ ]*?)></(\1)>', ''),
                    # Remove nested <span>.
                    (r'(<span>[.\s\S]*?</span>)', remove_span_tag),
                    (r'(<span>[.\s\S]*?</span>)', remove_span_tag))

    for pattern, replace in replacements:
        html = re.sub(pattern, replace, html)

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
    # questiontext should start with the question name as its title and between
    # <h3> tags. <span> tags should not exist.
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
        return f'Unable to fix "{setting}"!'

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
                    response = input(f'Change "{setting}" value? [Y/N] ')
                    fix_value = (response and response in 'yY')

                if fix_value:
                    if isinstance(value, list) and value:
                        value = value[0]
                    if issue := _fix_setting(category, question, setting,
                                             value, sep):
                        print(f'\t[{setting}] {issue}')
                    else:
                        print(f'\t[{setting}] changed!')
                print()

        if set_values:
            _add_CDATA(question)

    if set_values:
        tree.write(outfile, encoding='UTF-8', xml_declaration=True)

    return all_valid


def main():
    """Process command line arguments."""

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('file', help='Quiz XML file.')
    parser.add_argument('-l', '--list_values', action='store_true',
                        help='List suggested values and exit.')
    parser.add_argument('-s', '--set_values', action='store_true',
                        help='Set values, writing to a new file.')
    parser.add_argument('-o', '--outfile',
                        help='Output file name.')
    parser.add_argument('-y', '--yes_to_all', action='store_true',
                        help='Answer YES to any interactions.')
    parser.add_argument('-i', '--ignore', nargs='*', default=[],
                        help='Ignore given settings.')
    args = parser.parse_args()

    if args.list_values:
        print('Suggested values:')
        _print_dict(DEFAULTS)
    else:
        check(args.file, DEFAULTS, args.outfile, set_values=args.set_values,
              yes_to_all=args.yes_to_all, ignore_list=args.ignore)


if __name__ == '__main__':
    main()
