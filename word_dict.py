import pickle


def get_vocab(corpus1, corpus2):
    """
    构建词汇表的函数。

    Args:
        corpus1 (list): 第一个语料库，每个条目为一个列表。
        corpus2 (list): 第二个语料库，每个条目为一个列表。

    Returns:
        set: 包含两个语料库中所有唯一词汇的集合。
    """
    word_vocab = set()
    for corpus in [corpus1, corpus2]:
        for entry in corpus:
            word_vocab.update(entry[1][0])  # 更新词汇表
            word_vocab.update(entry[1][1])
            word_vocab.update(entry[2][0])
            word_vocab.update(entry[3])
    print(len(word_vocab))
    return word_vocab


def load_pickle(filename):
    """
    加载pickle文件的函数。

    Args:
        filename (str): pickle文件路径。

    Returns:
        object: pickle文件中反序列化得到的对象。
    """
    try:
        with open(filename, 'rb') as f:
            data = pickle.load(f)
    except IOError:
        print(f"Error: Failed to open or read {filename}")
        data = None
    return data


def vocab_processing(filepath1, filepath2, save_path):
    """
    处理词汇表的函数，将结果保存到文件中。

    Args:
        filepath1 (str): 第一个输入数据文件路径。
        filepath2 (str): 第二个输入数据文件路径。
        save_path (str): 保存词汇表结果的文件路径。
    """
    try:
        # 读取文件1和文件2中的数据
        with open(filepath1, 'r') as f:
            total_data1 = set(eval(f.read()))
        with open(filepath2, 'r') as f:
            total_data2 = eval(f.read())

        # 构建词汇表，排除文件1中已有的词汇
        word_set = get_vocab(total_data1, total_data2)

        excluded_words = total_data1.intersection(word_set)
        word_set = word_set - excluded_words

        print(len(total_data1))
        print(len(word_set))

        # 将词汇表写入保存路径
        with open(save_path, 'w') as f:
            f.write(str(word_set))

    except IOError:
        print(f"Error: Failed to open or read files {filepath1} or {filepath2}")
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")


if __name__ == "__main__":
    # 定义文件路径
    python_hnn = './data/python_hnn_data_teacher.txt'
    python_staqc = './data/staqc/python_staqc_data.txt'
    python_word_dict = './data/word_dict/python_word_vocab_dict.txt'

    sql_hnn = './data/sql_hnn_data_teacher.txt'
    sql_staqc = './data/staqc/sql_staqc_data.txt'
    sql_word_dict = './data/word_dict/sql_word_vocab_dict.txt'

    new_sql_staqc = './ulabel_data/staqc/sql_staqc_unlabeled_data.txt'
    new_sql_large = './ulabel_data/large_corpus/multiple/sql_large_multiple_unlabeled.txt'
    large_word_dict_sql = './ulabel_data/sql_word_dict.txt'

    # 执行词汇表处理函数
    vocab_processing(sql_word_dict, new_sql_large, large_word_dict_sql)
