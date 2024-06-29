# -*- coding: utf-8 -*-
import re
import sqlparse  # 0.4.2

# 骆驼命名法
import inflection

# 词性还原
from nltk import pos_tag
from nltk.stem import WordNetLemmatizer

wnler = WordNetLemmatizer()

# 词干提取
from nltk.corpus import wordnet

#############################################################################
# 常量定义，用于标识不同类型的SQL元素
OTHER = 0
FUNCTION = 1
BLANK = 2
KEYWORD = 3
INTERNAL = 4

TABLE = 5
COLUMN = 6
INTEGER = 7
FLOAT = 8
HEX = 9
STRING = 10
WILDCARD = 11

SUBQUERY = 12

DUD = 13

# 将类型码转换为对应的字符串表示
ttypes = {
    0: "OTHER",
    1: "FUNCTION",
    2: "BLANK",
    3: "KEYWORD",
    4: "INTERNAL",
    5: "TABLE",
    6: "COLUMN",
    7: "INTEGER",
    8: "FLOAT",
    9: "HEX",
    10: "STRING",
    11: "WILDCARD",
    12: "SUBQUERY",
    13: "DUD"
}

# 正则表达式扫描器，用于分割和识别SQL中的不同部分
scanner = re.Scanner([
    (r"\[[^\]]*\]", lambda scanner, token: token),
    (r"\+", lambda scanner, token: "REGPLU"),
    (r"\*", lambda scanner, token: "REGAST"),
    (r"%", lambda scanner, token: "REGCOL"),
    (r"\^", lambda scanner, token: "REGSTA"),
    (r"\$", lambda scanner, token: "REGEND"),
    (r"\?", lambda scanner, token: "REGQUE"),
    (r"[\.~``;_a-zA-Z0-9\s=:\{\}\-\\]+", lambda scanner, token: "REFRE"),
    (r'.', lambda scanner, token: None),
])

# ---------------------子函数1：代码的规则--------------------
def tokenizeRegex(s):
    """
    使用正则表达式扫描器分割输入字符串
    """
    results = scanner.scan(s)[0]
    return results

# ---------------------子函数2：代码的规则--------------------
class SqlangParser:
    """
    SQL语言解析器类
    """

    @staticmethod
    def sanitizeSql(sql):
        """
        对输入SQL字符串进行预处理，标准化格式并替换保留字
        """
        s = sql.strip().lower()
        if not s.endswith(";"):
            s += ';'
        s = re.sub(r'\(', r' ( ', s)
        s = re.sub(r'\)', r' ) ', s)
        words = ['index', 'table', 'day', 'year', 'user', 'text']
        for word in words:
            s = re.sub(r'([^\w])' + word + r'$', r'\1' + word + '1', s)
            s = re.sub(r'([^\w])' + word + r'([^\w])', r'\1' + word + '1' + r'\2', s)
        s = s.replace('#', '')
        return s

    def parseStrings(self, tok):
        """
        解析SQL字符串，将其转换为规范化形式
        """
        if isinstance(tok, sqlparse.sql.TokenList):
            for c in tok.tokens:
                self.parseStrings(c)
        elif tok.ttype == STRING:
            if self.regex:
                tok.value = ' '.join(tokenizeRegex(tok.value))
            else:
                tok.value = "CODSTR"

    def renameIdentifiers(self, tok):
        """
        重命名SQL标识符，避免冲突
        """
        if isinstance(tok, sqlparse.sql.TokenList):
            for c in tok.tokens:
                self.renameIdentifiers(c)
        elif tok.ttype == COLUMN:
            if str(tok) not in self.idMap["COLUMN"]:
                colname = "col" + str(self.idCount["COLUMN"])
                self.idMap["COLUMN"][str(tok)] = colname
                self.idMapInv[colname] = str(tok)
                self.idCount["COLUMN"] += 1
            tok.value = self.idMap["COLUMN"][str(tok)]
        elif tok.ttype == TABLE:
            if str(tok) not in self.idMap["TABLE"]:
                tabname = "tab" + str(self.idCount["TABLE"])
                self.idMap["TABLE"][str(tok)] = tabname
                self.idMapInv[tabname] = str(tok)
                self.idCount["TABLE"] += 1
            tok.value = self.idMap["TABLE"][str(tok)]

        elif tok.ttype == FLOAT:
            tok.value = "CODFLO"
        elif tok.ttype == INTEGER:
            tok.value = "CODINT"
        elif tok.ttype == HEX:
            tok.value = "CODHEX"

    def __hash__(self):
        """
        返回解析器对象的哈希值
        """
        return hash(tuple([str(x) for x in self.tokensWithBlanks]))

    def __init__(self, sql, regex=False, rename=True):
        """
        初始化解析器对象
        """
        self.sql = SqlangParser.sanitizeSql(sql)

        self.idMap = {"COLUMN": {}, "TABLE": {}}
        self.idMapInv = {}
        self.idCount = {"COLUMN": 0, "TABLE": 0}
        self.regex = regex

        self.parseTreeSentinel = False
        self.tableStack = []

        self.parse = sqlparse.parse(self.sql)
        self.parse = [self.parse[0]]

        self.removeWhitespaces(self.parse[0])
        self.identifyLiterals(self.parse[0])
        self.parse[0].ptype = SUBQUERY
        self.identifySubQueries(self.parse[0])
        self.identifyFunctions(self.parse[0])
        self.identifyTables(self.parse[0])

        self.parseStrings(self.parse[0])

        if rename:
            self.renameIdentifiers(self.parse[0])

        self.tokens = SqlangParser.getTokens(self.parse)

    @staticmethod
    def getTokens(parse):
        """
        提取解析树中的所有标记
        """
        flatParse = []
        for expr in parse:
            for token in expr.flatten():
                if token.ttype == STRING:
                    flatParse.extend(str(token).split(' '))
                else:
                    flatParse.append(str(token))
        return flatParse

    def removeWhitespaces(self, tok):
        """
        移除SQL标记中的空白字符
        """
        if isinstance(tok, sqlparse.sql.TokenList):
            tmpChildren = []
            for c in tok.tokens:
                if not c.is_whitespace:
                    tmpChildren.append(c)

            tok.tokens = tmpChildren
            for c in tok.tokens:
                self.removeWhitespaces(c)

    def identifySubQueries(self, tokenList):
        """
        识别并标记子查询
        """
        isSubQuery = False

        for tok in tokenList.tokens:
            if isinstance(tok, sqlparse.sql.TokenList):
                subQuery = self.identifySubQueries(tok)
                if subQuery and isinstance(tok, sqlparse.sql.Parenthesis):
                    tok.ttype = SUBQUERY
            elif str(tok).lower() == "select":
                isSubQuery = True
        return isSubQuery

    def identifyLiterals(self, tokenList):
        """
        识别并标记各种SQL字面量
        """
        blankTokens = [sqlparse.tokens.Name, sqlparse.tokens.Name.Placeholder]
        blankTokenTypes = [sqlparse.sql.Identifier]

        for tok in tokenList.tokens:
            if isinstance(tok, sqlparse.sql.TokenList):
                tok.ptype = INTERNAL
                self.identifyLiterals(tok)
            elif tok.ttype in [sqlparse.tokens.Keyword, sqlparse.tokens.Keyword.DML] or str(tok).lower() == "select":
                tok.ttype = KEYWORD
            elif tok.ttype in [sqlparse.tokens.Number.Integer, sqlparse.tokens.Literal.Number.Integer]:
                tok.ttype = INTEGER
            elif tok.ttype in [sqlparse.tokens.Number.Hexadecimal, sqlparse.tokens.Literal.Number.Hexadecimal]:
                tok.ttype = HEX
            elif tok.ttype in [sqlparse.tokens.Number.Float, sqlparse.tokens.Literal.Number.Float]:
                tok.ttype = FLOAT
            elif tok.ttype in [
                    sqlparse.tokens.String.Symbol, sqlparse.tokens.String.Single,
                    sqlparse.tokens.Literal.String.Single, sqlparse.tokens.Literal.String.Symbol]:
                tok.ttype = STRING
            elif tok.ttype == sqlparse.tokens.Wildcard:
                tok.ttype = WILDCARD
            elif tok.ttype in blankTokens or isinstance(tok, blankTokenTypes[0]):
                tok.ttype = COLUMN

    def identifyFunctions(self, tokenList):
        """
        识别并标记SQL函数
        """
        for tok in tokenList.tokens:
            if isinstance(tok, sqlparse.sql.Function):
                self.parseTreeSentinel = True
            elif isinstance(tok, sqlparse.sql.Parenthesis):
                self.parseTreeSentinel = False
            if self.parseTreeSentinel:
                tok.ttype = FUNCTION
            if isinstance(tok, sqlparse.sql.TokenList):
                self.identifyFunctions(tok)

    def identifyTables(self, tokenList):
        """
        识别并标记SQL表名
        """
        if tokenList.ptype == SUBQUERY:
            self.tableStack.append(False)

        for i in range(len(tokenList.tokens)):
            prevtok = tokenList.tokens[i - 1] if i > 0 else None
            tok = tokenList.tokens[i]

            if str(tok) == "." and tok.ttype == sqlparse.tokens.Punctuation and prevtok and prevtok.ttype == COLUMN:
                prevtok.ttype = TABLE

            elif str(tok).lower() == "from" and tok.ttype == sqlparse.tokens.Keyword:
                self.tableStack[-1] = True

            elif str(tok).lower() in ["where", "on", "group", "order", "union"] and tok.ttype == sqlparse.tokens.Keyword:
                self.tableStack[-1] = False

            if isinstance(tok, sqlparse.sql.TokenList):
                self.identifyTables(tok)
            elif tok.ttype == COLUMN and self.tableStack[-1]:
                tok.ttype = TABLE

        if tokenList.ptype == SUBQUERY:
            self.tableStack.pop()

    def __str__(self):
        """
        返回解析器对象的字符串表示形式
        """
        return ' '.join([str(tok) for tok in self.tokens])

    def parseSql(self):
        """
        返回解析后的SQL字符串列表
        """
        return [str(tok) for tok in self.tokens]


#############################################################################

#############################################################################
# 缩略词处理
def revert_abbrev(line):
    """
    还原英文缩略词
    """
    pat_is = re.compile(r"\b(it|he|she|that|this|there|here)\"s\b", re.I)
    pat_s1 = re.compile(r"(?<=[a-zA-Z])\"s\b")
    pat_s2 = re.compile(r"(?<=s)\"s?\b")
    pat_not = re.compile(r"(?<=[a-zA-Z])n\"t\b")
    pat_would = re.compile(r"(?<=[a-zA-Z])\"d\b")
    pat_will = re.compile(r"(?<=[a-zA-Z])\"ll\b")
    pat_am = re.compile(r"(?<=\b[Ii])\"m\b")
    pat_are = re.compile(r"(?<=[a-zA-Z])\"re\b")
    pat_ve = re.compile(r"(?<=[a-zA-Z])\"ve\b")

    line = pat_is.sub(r"\1 is", line)
    line = pat_s1.sub("", line)
    line = pat_s2.sub("", line)
    line = pat_not.sub(" not", line)
    line = pat_would.sub(" would", line)
    line = pat_will.sub(" will", line)
    line = pat_am.sub(" am", line)
    line = pat_are.sub(" are", line)
    line = pat_ve.sub(" have", line)

    return line

# 获取词性
def get_wordpos(tag):
    if tag.startswith('J'):
        return wordnet.ADJ
    elif tag.startswith('V'):
        return wordnet.VERB
    elif tag.startswith('N'):
        return wordnet.NOUN
    elif tag.startswith('R'):
        return wordnet.ADV
    else:
        return None


# ---------------------子函数1：句子的去冗--------------------
def process_nl_line(line):
    """
    句子预处理：去除冗余空白和括号内容，转换为下划线命名法
    """
    line = revert_abbrev(line)
    line = re.sub('\t+', '\t', line)
    line = re.sub('\n+', '\n', line)
    line = line.replace('\n', ' ')
    line = line.replace('\t', ' ')
    line = re.sub(' +', ' ', line)
    line = line.strip()
    # 骆驼命名转下划线
    line = inflection.underscore(line)

    # 去除括号里内容
    space = re.compile(r"\([^\(|^\)]+\)")
    line = re.sub(space, '', line)
    # 去除末尾.和空格
    line = line.strip()
    return line


# ---------------------子函数2：句子的分词--------------------
def process_sent_word(line):
    """
    句子分词：提取单词、替换特殊字符和数字，词性还原和提取词干
    """
    # 找单词
    line = re.findall(r"[\w]+|[^\s\w]", line)
    line = ' '.join(line)

    # 替换小数
    decimal = re.compile(r"\d+(\.\d+)+")
    line = re.sub(decimal, 'TAGINT', line)
    # 替换字符串
    string = re.compile(r'\"[^\"]+\"')
    line = re.sub(string, 'TAGSTR', line)
    # 替换十六进制
    hex_decimal = re.compile(r"0[xX][A-Fa-f0-9]+")
    line = re.sub(hex_decimal, 'TAGINT', line)
    # 替换数字
    number = re.compile(r"\s?\d+\s?")
    line = re.sub(number, ' TAGINT ', line)
    # 替换字符
    other = re.compile(r"(?<![A-Z|a-z|_])\d+[A-Za-z]+")
    line = re.sub(other, 'TAGOER', line)
    cut_words = line.split(' ')
    # 全部小写化
    cut_words = [x.lower() for x in cut_words]
    # 词性标注
    word_tags = pos_tag(cut_words)
    tags_dict = dict(word_tags)
    word_list = []
    for word in cut_words:
        word_pos = get_wordpos(tags_dict[word])
        if word_pos:
            # 词性还原
            word = wnler.lemmatize(word, pos=word_pos)
        # 词干提取
        word = wordnet.morphy(word) if wordnet.morphy(word) else word
        word_list.append(word)
    return word_list


#############################################################################

def filter_all_invachar(line):
    """
    去除非常用符号，防止解析错误；包括去除换行符和制表符
    """
    line = re.sub('[^(0-9|a-z|A-Z|\-|_|\'|\"|\-|\(|\)|\n)]+', ' ', line)
    # 中横线
    line = re.sub('-+', '-', line)
    # 下划线
    line = re.sub('_+', '_', line)
    # 去除横杠
    line = line.replace('|', ' ').replace('¦', ' ')
    return line


def filter_part_invachar(line):
    """
    去除部分非常用符号，防止解析错误；包括去除换行符和制表符
    """
    line = re.sub('[^(0-9|a-z|A-Z|\-|#|/|_|,|\'|=|>|<|\"|\-|\\|\(|\)|\?|\.|\*|\+|\[|\]|\^|\{|\}|\n)]+', ' ', line)
    # 中横线
    line = re.sub('-+', '-', line)
    # 下划线
    line = re.sub('_+', '_', line)
    # 去除横杠
    line = line.replace('|', ' ').replace('¦', ' ')
    return line


########################主函数：代码的tokens#################################
def sqlang_code_parse(line):
    """
    解析代码行，生成tokens
    """
    line = filter_part_invachar(line)
    line = re.sub('\.+', '.', line)
    line = re.sub('\t+', '\t', line)
    line = re.sub('\n+', '\n', line)
    line = re.sub(' +', ' ', line)

    line = re.sub('>>+', '', line)  # 新增加
    line = re.sub(r"\d+(\.\d+)+", 'number', line)  # 新增加 替换小数

    line = line.strip('\n').strip()
    line = re.findall(r"[\w]+|[^\s\w]", line)
    line = ' '.join(line)

    try:
        query = SqlangParser(line, regex=True)
        typedCode = query.parseSql()
        typedCode = typedCode[:-1]
        # 骆驼命名转下划线
        typedCode = inflection.underscore(' '.join(typedCode)).split(' ')

        cut_tokens = [re.sub("\s+", " ", x.strip()) for x in typedCode]
        # 全部小写化
        token_list = [x.lower() for x in cut_tokens]
        # 列表里包含 '' 和' '
        token_list = [x.strip() for x in token_list if x.strip() != '']
        # 返回列表
        return token_list
    except Exception as e:
        return str(e)


########################主函数：句子的tokens##################################

def sqlang_query_parse(line):
    """
    解析自然语言查询，生成tokens
    """
    line = filter_all_invachar(line)
    line = process_nl_line(line)
    word_list = process_sent_word(line)
    # 分完词后,再去掉括号
    for i in range(len(word_list)):
        if re.findall('[\(\)]', word_list[i]):
            word_list[i] = ''
    # 列表里包含 '' 或 ' '
    word_list = [x.strip() for x in word_list if x.strip() != '']
    # 解析可能为空
    return word_list


def sqlang_context_parse(line):
    """
    解析自然语言上下文，生成tokens
    """
    line = filter_part_invachar(line)
    line = process_nl_line(line)
    word_list = process_sent_word(line)
    # 列表里包含 '' 或 ' '
    word_list = [x.strip() for x in word_list if x.strip() != '']
    # 解析可能为空
    return word_list


#######################主函数：句子的tokens##################################


if __name__ == '__main__':
    print(sqlang_code_parse(
        '""geometry": {"type": "Polygon" , 111.676,"coordinates": [[[6.69245274714546, 51.1326962505233], [6.69242714158622, 51.1326908883821], [6.69242919794447, 51.1326955158344], [6.69244041615532, 51.1326998744549], [6.69244125953742, 51.1327001609189], [6.69245274714546, 51.1326962505233]]]} How to 123 create a (SQL  Server function) to "join" multiple rows from a subquery into a single delimited field?'))
    print(sqlang_query_parse("change row_height and column_width in libreoffice calc use python tagint"))
    print(sqlang_query_parse('MySQL Administrator Backups: "Compatibility Mode", What Exactly is this doing?'))
    print(sqlang_code_parse(
        '>UPDATE Table1 \n SET Table1.col1 = Table2.col1 \n Table1.col2 = Table2.col2 FROM \n Table2 WHERE \n Table1.id =  Table2.id'))
    print(sqlang_code_parse("SELECT\n@supplyFee:= 0\n@demandFee := 0\n@charedFee := 0\n"))
    print(sqlang_code_parse('@prev_sn := SerialNumber,\n@prev_toner := Remain_Toner_Black\n'))
    print(sqlang_code_parse(
        ' ;WITH QtyCTE AS (\n  SELECT  [Category] = c.category_name\n          , [RootID] = c.category_id\n          , [ChildID] = c.category_id\n  FROM    Categories c\n  UNION ALL \n  SELECT  cte.Category\n          , cte.RootID\n          , c.category_id\n  FROM    QtyCTE cte\n          INNER JOIN Categories c ON c.father_id = cte.ChildID\n)\nSELECT  cte.RootID\n        , cte.Category\n        , COUNT(s.sales_id)\nFROM    QtyCTE cte\n        INNER JOIN Sales s ON s.category_id = cte.ChildID\nGROUP BY cte.RootID, cte.Category\nORDER BY cte.RootID\n'))
    print(sqlang_code_parse(
        "DECLARE @Table TABLE (ID INT, Code NVARCHAR(50), RequiredID INT);\n\nINSERT INTO @Table (ID, Code, RequiredID)   VALUES\n    (1, 'Physics', NULL),\n    (2, 'Advanced Physics', 1),\n    (3, 'Nuke', 2),\n    (4, 'Health', NULL);    \n\nDECLARE @DefaultSeed TABLE (ID INT, Code NVARCHAR(50), RequiredID INT);\n\nWITH hierarchy \nAS (\n    --anchor\n    SELECT  t.ID , t.Code , t.RequiredID\n    FROM @Table AS t\n    WHERE t.RequiredID IS NULL\n\n    UNION ALL   \n\n    --recursive\n    SELECT  t.ID \n          , t.Code \n          , h.ID        \n    FROM hierarchy AS h\n        JOIN @Table AS t \n            ON t.RequiredID = h.ID\n    )\n\nINSERT INTO @DefaultSeed (ID, Code, RequiredID)\nSELECT  ID \n        , Code \n        , RequiredID\nFROM hierarchy\nOPTION (MAXRECURSION 10)\n\n\nDECLARE @NewSeed TABLE (ID INT IDENTITY(10, 1), Code NVARCHAR(50), RequiredID INT)\n\nDeclare @MapIds Table (aOldID int,aNewID int)\n\n;MERGE INTO @NewSeed AS TargetTable\nUsing @DefaultSeed as Source on 1=0\nWHEN NOT MATCHED then\n Insert (Code,RequiredID)\n Values\n (Source.Code,Source.RequiredID)\nOUTPUT Source.ID ,inserted.ID into @MapIds;\n\n\nUpdate @NewSeed Set RequiredID=aNewID\nfrom @MapIds\nWhere RequiredID=aOldID\n\n\n/*\n--@NewSeed should read like the following...\n[ID]  [Code]           [RequiredID]\n10....Physics..........NULL\n11....Health...........NULL\n12....AdvancedPhysics..10\n13....Nuke.............12\n*/\n\nSELECT *\nFROM @NewSeed\n"))
