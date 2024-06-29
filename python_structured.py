import re
import ast

# 导入token和tokenize用于词法分析
import token
import tokenize

# 导入NLTK用于分词
from nltk import wordpunct_tokenize

# StringIO用于字符串操作
from io import StringIO

# 导入inflection用于CamelCase转换为snake_case
import inflection

# 导入NLTK用于词性标注和词形还原
from nltk import pos_tag
from nltk.stem import WordNetLemmatizer

# 导入WordNet语料库用于词形还原
from nltk.corpus import wordnet

# 创建全局的WordNet词形还原实例
wnl = WordNetLemmatizer()

# 用于变量赋值和for循环的正则表达式模式
PATTERN_VAR_EQUAL = re.compile(r"(\s*[_a-zA-Z][_a-zA-Z0-9]*\s*)(,\s*[_a-zA-Z][_a-zA-Z0-9]*\s*)*=")
PATTERN_VAR_FOR = re.compile(r"for\s+[_a-zA-Z][_a-zA-Z0-9]*\s*(,\s*[_a-zA-Z][_a-zA-Z0-9]*)*\s+in")


def repair_program_io(code):
    """
    修复程序输入输出的代码块。

    这个函数识别并修复通常在notebook或REPL环境中出现的代码块，
    这些代码块中包含输入、输出和继续提示符。

    :param code: str，包含潜在提示符标记的原始代码字符串
    :return: str，去除提示符标记后的修复代码
             list of str，按提示符标记分割的代码块列表
    """
    # notebook和REPL代码的正则表达式模式
    pattern_case1_in = re.compile(r"In ?\[\d+]: ?")
    pattern_case1_out = re.compile(r"Out ?\[\d+]: ?")
    pattern_case1_cont = re.compile(r"( )+\.+: ?")
    pattern_case2_in = re.compile(r">>> ?")
    pattern_case2_cont = re.compile(r"\.\.\. ?")

    patterns = [pattern_case1_in, pattern_case1_out, pattern_case1_cont, pattern_case2_in, pattern_case2_cont]

    # 按行分割代码
    lines = code.split("\n")
    lines_flags = [0 for _ in range(len(lines))]

    code_list = []  # 存储代码块的字符串列表

    # 匹配模式以识别代码块
    for line_idx in range(len(lines)):
        line = lines[line_idx]
        for pattern_idx in range(len(patterns)):
            if re.match(patterns[pattern_idx], line):
                lines_flags[line_idx] = pattern_idx + 1
                break
    lines_flags_string = "".join(map(str, lines_flags))

    bool_repaired = False

    # 如果不需要修复
    if lines_flags.count(0) == len(lines_flags):
        repaired_code = code
        code_list = [code]
        bool_repaired = True

    # 如果代码匹配典型模式
    elif re.match(r"(0*1+3*2*0*)+", lines_flags_string) or re.match(r"(0*4+5*0*)+", lines_flags_string):
        repaired_code = ""
        pre_idx = 0
        sub_block = ""
        if lines_flags[0] == 0:
            flag = 0
            while flag == 0:
                repaired_code += lines[pre_idx] + "\n"
                pre_idx += 1
                flag = lines_flags[pre_idx]
            sub_block = repaired_code
            code_list.append(sub_block.strip())
            sub_block = ""

        for idx in range(pre_idx, len(lines_flags)):
            if lines_flags[idx] != 0:
                repaired_code += re.sub(patterns[lines_flags[idx] - 1], "", lines[idx]) + "\n"
                if len(sub_block.strip()) and (idx > 0 and lines_flags[idx - 1] == 0):
                    code_list.append(sub_block.strip())
                    sub_block = ""
                sub_block += re.sub(patterns[lines_flags[idx] - 1], "", lines[idx]) + "\n"
            else:
                if len(sub_block.strip()) and (idx > 0 and lines_flags[idx - 1] != 0):
                    code_list.append(sub_block.strip())
                    sub_block = ""
                sub_block += lines[idx] + "\n"

        if len(sub_block.strip()):
            code_list.append(sub_block.strip())

        if len(repaired_code.strip()) != 0:
            bool_repaired = True

    if not bool_repaired:
        repaired_code = ""
        sub_block = ""
        bool_after_Out = False
        for idx in range(len(lines_flags)):
            if lines_flags[idx] != 0:
                if lines_flags[idx] == 2:
                    bool_after_Out = True
                else:
                    bool_after_Out = False
                repaired_code += re.sub(patterns[lines_flags[idx] - 1], "", lines[idx]) + "\n"

                if len(sub_block.strip()) and (idx > 0 and lines_flags[idx - 1] == 0):
                    code_list.append(sub_block.strip())
                    sub_block = ""
                sub_block += re.sub(patterns[lines_flags[idx] - 1], "", lines[idx]) + "\n"
            else:
                if not bool_after_Out:
                    repaired_code += lines[idx] + "\n"

                if len(sub_block.strip()) and (idx > 0 and lines_flags[idx - 1] != 0):
                    code_list.append(sub_block.strip())
                    sub_block = ""
                sub_block += lines[idx] + "\n"

    return repaired_code, code_list


def get_vars(ast_root):
    """
    从AST中提取变量名。

    :param ast_root: AST的根节点
    :return: list，排序后的变量名列表
    """
    return sorted(
        {node.id for node in ast.walk(ast_root) if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load)})


def get_vars_heuristics(code):
    """
    使用启发式方法从代码中提取变量名。

    :param code: str，源代码字符串
    :return: set，提取出的变量名集合
    """
    varnames = set()
    # 去除空行
    code_lines = [_ for _ in code.split("\n") if len(_.strip())]

    start = 0
    end = len(code_lines) - 1
    bool_success = False

    # 尝试解析代码，直到成功或代码行数减少到零
    while not bool_success and end >= start:
        try:
            root = ast.parse("\n".join(code_lines[start:end]))
        except:
            end -= 1
        else:
            bool_success = True

    # 使用AST解析成功后提取变量名
    varnames = varnames.union(set(get_vars(root)))

    # 对未解析的代码行使用正则表达式匹配变量名
    for line in code_lines[end:]:
        line = line.strip()
        try:
            root = ast.parse(line)
        except:
            pattern_var_equal_matched = re.match(PATTERN_VAR_EQUAL, line)
            if pattern_var_equal_matched:
                match = pattern_var_equal_matched.group()[:-1]  # 移除 "="
                varnames = varnames.union(set([_.strip() for _ in match.split(",")]))

            pattern_var_for_matched = re.search(PATTERN_VAR_FOR, line)
            if pattern_var_for_matched:
                match = pattern_var_for_matched.group()[3:-2]  # 移除 "for" 和 "in"
                varnames = varnames.union(set([_.strip() for _ in match.split(",")]))
        else:
            varnames = varnames.union(get_vars(root))

    return varnames


def PythonParser(code):
    """
    解析Python代码并进行词法分析。

    :param code: str，源代码字符串
    :return: tuple，包含词法分析后的代码、是否变量提取失败、是否词法分析失败
    """
    bool_failed_var = False
    bool_failed_token = False

    try:
        root = ast.parse(code)
        varnames = set(get_vars(root))
    except:
        repaired_code, _ = repair_program_io(code)
        try:
            root = ast.parse(repaired_code)
            varnames = set(get_vars(root))
        except:
            bool_failed_var = True
            varnames = get_vars_heuristics(code)

    tokenized_code = []

    def first_trial(_code):
        if len(_code) == 0:
            return True
        try:
            g = tokenize.generate_tokens(StringIO(_code).readline)
            term = next(g)
        except:
            return False
        else:
            return True

    bool_first_success = first_trial(code)
    while not bool_first_success:
        code = code[1:]
        bool_first_success = first_trial(code)

    g = tokenize.generate_tokens(StringIO(code).readline)
    term = next(g)

    bool_finished = False
    while not bool_finished:
        term_type = term[0]
        lineno = term[2][0] - 1
        posno = term[3][1] - 1

        # 处理不同类型的token
        if token.tok_name[term_type] in {"NUMBER", "STRING", "NEWLINE"}:
            tokenized_code.append(token.tok_name[term_type])
        elif not token.tok_name[term_type] in {"COMMENT", "ENDMARKER"} and len(term[1].strip()):
            candidate = term[1].strip()
            if candidate not in varnames:
                tokenized_code.append(candidate)
            else:
                tokenized_code.append("VAR")

        bool_success_next = False
        while not bool_success_next:
            try:
                term = next(g)
            except StopIteration:
                bool_finished = True
                break
            except:
                bool_failed_token = True
                code_lines = code.split("\n")
                if lineno > len(code_lines) - 1:
                    print(sys.exc_info())
                else:
                    failed_code_line = code_lines[lineno]
                    if posno < len(failed_code_line) - 1:
                        failed_code_line = failed_code_line[posno:]
                        tokenized_failed_code_line = wordpunct_tokenize(failed_code_line)
                        tokenized_code += tokenized_failed_code_line
                    if lineno < len(code_lines) - 1:
                        code = "\n".join(code_lines[lineno + 1:])
                        g = tokenize.generate_tokens(StringIO(code).readline)
                    else:
                        bool_finished = True
                        break
            else:
                bool_success_next = True

    return tokenized_code, bool_failed_var, bool_failed_token


import re
import ast
import inflection
import tokenize
from io import StringIO


# 定义用于替换缩写的正则表达式模式
def revert_abbrev(line):
    """
    将行中的缩写形式还原为完整形式。

    :param line: str，包含缩写的字符串
    :return: str，包含完整形式的字符串
    """
    pat_is = re.compile(r"(it|he|she|that|this|there|here)('s)", re.I)
    pat_s1 = re.compile(r"(?<=[a-zA-Z])'s")
    pat_s2 = re.compile(r"(?<=s)'s?")
    pat_not = re.compile(r"(?<=[a-zA-Z])n't")
    pat_would = re.compile(r"(?<=[a-zA-Z])'d")
    pat_will = re.compile(r"(?<=[a-zA-Z])'ll")
    pat_am = re.compile(r"(?<=[I|i])'m")
    pat_are = re.compile(r"(?<=[a-zA-Z])'re")
    pat_ve = re.compile(r"(?<=[a-zA-Z])'ve")

    line = pat_is.sub(r"\1 is", line)
    line = pat_s1.sub(r" is", line)
    line = pat_s2.sub(r"s", line)
    line = pat_not.sub(r" not", line)
    line = pat_would.sub(r" would", line)
    line = pat_will.sub(r" will", line)
    line = pat_am.sub(r" am", line)
    line = pat_are.sub(r" are", line)
    line = pat_ve.sub(r" have", line)

    return line


def python_code_parse(line):
    """
    解析Python代码，进行预处理和词法分析。

    :param line: str，源代码字符串
    :return: list，包含代码token的列表
    """
    line = filter_part_invachar(line)
    line = re.sub(r'\.+', '.', line)
    line = re.sub(r'\t+', '\t', line)
    line = re.sub(r'\n+', '\n', line)
    line = re.sub(r'>>+', '', line)  # 新增处理 ">>"
    line = re.sub(r' +', ' ', line)
    line = line.strip('\n').strip()
    line = re.findall(r"[\w]+|[^\s\w]", line)
    line = ' '.join(line)

    try:
        typedCode, failed_var, failed_token = PythonParser(line)
        # 骆驼命名转下划线
        typedCode = inflection.underscore(' '.join(typedCode)).split(' ')

        cut_tokens = [re.sub(r"\s+", " ", x.strip()) for x in typedCode]
        # 全部小写化
        token_list = [x.lower() for x in cut_tokens]
        # 去除列表中的空字符串
        token_list = [x.strip() for x in token_list if x.strip() != '']
        return token_list
    except:
        return '-1000'


# 主函数：解析代码的tokens
def python_query_parse(line):
    """
    解析Python查询语句，进行预处理和分词。

    :param line: str，源查询字符串
    :return: list，包含查询词的列表
    """
    line = filter_all_invachar(line)
    line = process_nl_line(line)
    word_list = process_sent_word(line)
    # 去除括号
    word_list = ['' if re.findall('[()]', word) else word for word in word_list]
    # 去除列表中的空字符串
    word_list = [x.strip() for x in word_list if x.strip() != '']
    return word_list


def python_context_parse(line):
    """
    解析Python上下文，进行预处理和分词。

    :param line: str，源上下文字符串
    :return: list，包含上下文词的列表
    """
    line = filter_part_invachar(line)
    # 处理驼峰命名
    line = process_nl_line(line)
    print(line)
    word_list = process_sent_word(line)
    # 去除列表中的空字符串
    word_list = [x.strip() for x in word_list if x.strip() != '']
    return word_list


# 主函数：句子的tokens
if __name__ == '__main__':
    # 测试解析查询语句
    print(python_query_parse("change row_height and column_width in libreoffice calc use python tagint"))
    print(python_query_parse('What is the standard way to add N seconds to datetime.time in Python?'))
    print(python_query_parse("Convert INT to VARCHAR SQL 11?"))
    print(python_query_parse(
        'python construct a dictionary {0: [0, 0, 0], 1: [0, 0, 1], 2: [0, 0, 2], 3: [0, 0, 3], ...,999: [9, 9, 9]}'))

    # 测试解析上下文
    print(python_context_parse(
        'How to calculateAnd the value of the sum of squares defined as \n 1^2 + 2^2 + 3^2 + ... +n2 until a user specified sum has been reached sql()'))
    print(python_context_parse('how do i display records (containing specific) information in sql() 11?'))
    print(python_context_parse('Convert INT to VARCHAR SQL 11?'))

    # 测试解析代码
    print(python_code_parse(
        'if(dr.HasRows)\n{\n // ....\n}\nelse\n{\n MessageBox.Show("ReservationAnd Number Does Not Exist","Error", MessageBoxButtons.OK, MessageBoxIcon.Asterisk);\n}'))
    print(python_code_parse('root -> 0.0 \n while root_ * root < n: \n root = root + 1 \n print(root * root)'))
    print(python_code_parse('root = 0.0 \n while root * root < n: \n root = root + 1 \n print(root * root)'))
    print(python_code_parse('n = 1 \n while n <= 100: \n n = n + 1 \n if n > 10: \n  break print(n)'))
    print(python_code_parse(
        "diayong(2) def sina_download(url, output_dir='.', merge=True, info_only=False, **kwargs):\n    if 'news.sina.com.cn/zxt' in url:\n        sina_zxt(url, output_dir=output_dir, merge=merge, info_only=info_only, **kwargs)\n  return\n\n    vid = match1(url, r'vid=(\\d+)')\n    if vid is None:\n        video_page = get_content(url)\n        vid = hd_vid = match1(video_page, r'hd_vid\\s*:\\s*\\'([^\\']+)\\'')\n  if hd_vid == '0':\n            vids = match1(video_page, r'[^\\w]vid\\s*:\\s*\\'([^\\']+)\\'').split('|')\n            vid = vids[-1]\n\n    if vid is None:\n        vid = match1(video_page, r'vid:\"?(\\d+)\"?')\n    if vid:\n   sina_download_by_vid(vid, output_dir=output_dir, merge=merge, info_only=info_only)\n    else:\n        vkey = match1(video_page, r'vkey\\s*:\\s*\"([^\"]+)\"')\n        if vkey is None:\n            vid = match1(url, r'#(\\d+)')\n            sina_download_by_vid(vid, output_dir=output_dir, merge=merge, info_only=info_only)\n            return\n        title = match1(video_page, r'title\\s*:\\s*\"([^\"]+)\"')\n        sina_download_by_vkey(vkey, title=title, output_dir=output_dir, merge=merge, info_only=info_only)"))

    print(python_code_parse('root = 0.0 \n while root * root < n: \n root = root + 1 \n print(root * root)'))
    print(python_code_parse('a = 1 \n for i in range(10): \n a += i \n print(a)'))
    print(python_code_parse('def foo(): \n    return "foo" \n foo()'))
