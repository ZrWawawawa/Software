import pickle
from collections import Counter

def load_pickle(filename):
    """
    加载 pickle 文件。
    :param filename: 文件路径
    :return: 加载的数据
    """
    with open(filename, 'rb') as f:
        data = pickle.load(f, encoding='iso-8859-1')
    return data

def split_data(total_data, qids):
    """
    根据 qids 划分数据为单个和多个类别。
    :param total_data: 总数据
    :param qids: 问题 ID 列表
    :return: 单个数据和多个数据
    """
    result = Counter(qids)
    total_data_single = []
    total_data_multiple = []
    for data in total_data:
        if result[data[0][0]] == 1:
            total_data_single.append(data)
        else:
            total_data_multiple.append(data)
    return total_data_single, total_data_multiple

def data_staqc_processing(filepath, save_single_path, save_multiple_path):
    """
    处理 STaQC 数据。
    :param filepath: 输入文件路径
    :param save_single_path: 单个数据保存路径
    :param save_multiple_path: 多个数据保存路径
    """
    with open(filepath, 'r') as f:
        total_data = eval(f.read())
    qids = [data[0][0] for data in total_data]
    total_data_single, total_data_multiple = split_data(total_data, qids)

    with open(save_single_path, "w") as f:
        f.write(str(total_data_single))
    with open(save_multiple_path, "w") as f:
        f.write(str(total_data_multiple))

def data_large_processing(filepath, save_single_path, save_multiple_path):
    """
    处理大规模数据。
    :param filepath: 输入文件路径
    :param save_single_path: 单个数据保存路径
    :param save_multiple_path: 多个数据保存路径
    """
    total_data = load_pickle(filepath)
    qids = [data[0][0] for data in total_data]
    total_data_single, total_data_multiple = split_data(total_data, qids)

    with open(save_single_path, 'wb') as f:
        pickle.dump(total_data_single, f)
    with open(save_multiple_path, 'wb') as f:
        pickle.dump(total_data_multiple, f)

def single_unlabeled_to_labeled(input_path, output_path):
    """
    将未标记的数据转换为标记的数据。
    :param input_path: 输入文件路径
    :param output_path: 输出文件路径
    """
    total_data = load_pickle(input_path)
    labels = [[data[0], 1] for data in total_data]
    total_data_sort = sorted(labels, key=lambda x: (x[0], x[1]))
    with open(output_path, "w") as f:
        f.write(str(total_data_sort))

if __name__ == "__main__":
    # 处理 STaQC Python 数据
    staqc_python_path = './ulabel_data/python_staqc_qid2index_blocks_unlabeled.txt'
    staqc_python_single_save = './ulabel_data/staqc/single/python_staqc_single.txt'
    staqc_python_multiple_save = './ulabel_data/staqc/multiple/python_staqc_multiple.txt'
    data_staqc_processing(staqc_python_path, staqc_python_single_save, staqc_python_multiple_save)

    # 处理 STaQC SQL 数据
    staqc_sql_path = './ulabel_data/sql_staqc_qid2index_blocks_unlabeled.txt'
    staqc_sql_single_save = './ulabel_data/staqc/single/sql_staqc_single.txt'
    staqc_sql_multiple_save = './ulabel_data/staqc/multiple/sql_staqc_multiple.txt'
    data_staqc_processing(staqc_sql_path, staqc_sql_single_save, staqc_sql_multiple_save)

    # 处理大规模 Python 数据
    large_python_path = './ulabel_data/python_codedb_qid2index_blocks_unlabeled.pickle'
    large_python_single_save = './ulabel_data/large_corpus/single/python_large_single.pickle'
    large_python_multiple_save = './ulabel_data/large_corpus/multiple/python_large_multiple.pickle'
    data_large_processing(large_python_path, large_python_single_save, large_python_multiple_save)

    # 处理大规模 SQL 数据
    large_sql_path = './ulabel_data/sql_codedb_qid2index_blocks_unlabeled.pickle'
    large_sql_single_save = './ulabel_data/large_corpus/single/sql_large_single.pickle'
    large_sql_multiple_save = './ulabel_data/large_corpus/multiple/sql_large_multiple.pickle'
    data_large_processing(large_sql_path, large_sql_single_save, large_sql_multiple_save)

    # 将未标记的数据转换为标记的数据
    large_sql_single_label_save = './ulabel_data/large_corpus/single/sql_large_single_label.txt'
    large_python_single_label_save = './ulabel_data/large_corpus/single/python_large_single_label.txt'
    single_unlabeled_to_labeled(large_sql_single_save, large_sql_single_label_save)
    single_unlabeled_to_labeled(large_python_single_save, large_python_single_label_save)
