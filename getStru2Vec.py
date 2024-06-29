import pickle
import multiprocessing
from python_structured import python_query_parse, python_code_parse, python_context_parse
from sqlang_structured import sqlang_query_parse, sqlang_code_parse, sqlang_context_parse


def multipro_python_query(data_list):
    return [python_query_parse(line) for line in data_list]


def multipro_python_code(data_list):
    return [python_code_parse(line) for line in data_list]


def multipro_python_context(data_list):
    return [['-10000'] if line == '-10000' else python_context_parse(line) for line in data_list]


def multipro_sqlang_query(data_list):
    return [sqlang_query_parse(line) for line in data_list]


def multipro_sqlang_code(data_list):
    return [sqlang_code_parse(line) for line in data_list]


def multipro_sqlang_context(data_list):
    return [['-10000'] if line == '-10000' else sqlang_context_parse(line) for line in data_list]


def parse(data_list, split_num, context_func, query_func, code_func):
    """
    使用多进程解析数据。

    :param data_list: 输入数据列表
    :param split_num: 分割数据的块大小
    :param context_func: 处理上下文的函数
    :param query_func: 处理查询的函数
    :param code_func: 处理代码的函数
    :return: 解析后的上下文数据、查询数据和代码数据
    """
    with multiprocessing.Pool() as pool:
        split_list = [data_list[i:i + split_num] for i in range(0, len(data_list), split_num)]

        context_data = [item for sublist in pool.map(context_func, split_list) for item in sublist]
        print(f'context条数：{len(context_data)}')

        query_data = [item for sublist in pool.map(query_func, split_list) for item in sublist]
        print(f'query条数：{len(query_data)}')

        code_data = [item for sublist in pool.map(code_func, split_list) for item in sublist]
        print(f'code条数：{len(code_data)}')

    return context_data, query_data, code_data


def main(lang_type, split_num, source_path, save_path, context_func, query_func, code_func):
    """
    主函数，处理数据并保存。

    :param lang_type: 语言类型
    :param split_num: 分割数据的块大小
    :param source_path: 输入数据文件路径
    :param save_path: 输出数据文件路径
    :param context_func: 处理上下文的函数
    :param query_func: 处理查询的函数
    :param code_func: 处理代码的函数
    """
    with open(source_path, 'rb') as f:
        corpus_lis = pickle.load(f)

    context_data, query_data, code_data = parse(corpus_lis, split_num, context_func, query_func, code_func)
    qids = [item[0] for item in corpus_lis]

    total_data = [[qids[i], context_data[i], code_data[i], query_data[i]] for i in range(len(qids))]

    with open(save_path, 'wb') as f:
        pickle.dump(total_data, f)

    print(f'{save_path} 数据处理完成')


if __name__ == '__main__':
    split_num = 1000  # 分块大小，可以根据需要调整

    # Python 数据处理
    staqc_python_path = './ulabel_data/python_staqc_qid2index_blocks_unlabeled.txt'
    staqc_python_save = '../hnn_process/ulabel_data/staqc/python_staqc_unlabled_data.pkl'

    main('python', split_num, staqc_python_path, staqc_python_save, multipro_python_context, multipro_python_query,
         multipro_python_code)

    # SQL 数据处理
    staqc_sql_path = './ulabel_data/sql_staqc_qid2index_blocks_unlabeled.txt'
    staqc_sql_save = './ulabel_data/staqc/sql_staqc_unlabled_data.pkl'

    main('sql', split_num, staqc_sql_path, staqc_sql_save, multipro_sqlang_context, multipro_sqlang_query,
         multipro_sqlang_code)

    # 大规模 Python 数据处理
    large_python_path = './ulabel_data/large_corpus/multiple/python_large_multiple.pickle'
    large_python_save = '../hnn_process/ulabel_data/large_corpus/multiple/python_large_multiple_unlable.pkl'

    main('python', split_num, large_python_path, large_python_save, multipro_python_context, multipro_python_query,
         multipro_python_code)

    # 大规模 SQL 数据处理
    large_sql_path = './ulabel_data/large_corpus/multiple/sql_large_multiple.pickle'
    large_sql_save = './ulabel_data/large_corpus/multiple/sql_large_multiple_unlable.pkl'

    main('sql', split_num, large_sql_path, large_sql_save, multipro_sqlang_context, multipro_sqlang_query,
         multipro_sqlang_code)
