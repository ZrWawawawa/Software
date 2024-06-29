import pickle
import numpy as np
from gensim.models import KeyedVectors


def trans_bin(text_file_path, trans_file_path):
    """
    将文本格式词向量文件保存为二进制文件。

    :param text_file_path: 文本格式的词向量文件路径
    :param trans_file_path: 转换后的二进制文件路径
    """
    wv_from_text = KeyedVectors.load_word2vec_format(text_file_path, binary=False)
    wv_from_text.init_sims(replace=True)
    wv_from_text.save(trans_file_path)


def get_new_dict(type_vec_path, type_word_path, final_vec_path, final_word_path):
    """
    构建新的词典和词向量矩阵。

    :param type_vec_path: 词向量文件路径
    :param type_word_path: 词典文件路径
    :param final_vec_path: 最终词向量保存路径
    :param final_word_path: 最终词典保存路径
    """
    model = KeyedVectors.load(type_vec_path, mmap='r')

    with open(type_word_path, 'r') as f:
        total_word = eval(f.read())

    word_dict = ['PAD', 'SOS', 'EOS', 'UNK']  # 其中0 PAD_ID, 1 SOS_ID, 2 EOS_ID, 3 UNK_ID

    fail_word = []
    rng = np.random.RandomState(None)
    pad_embedding = np.zeros((300,))
    sos_embedding = rng.uniform(-0.25, 0.25, (300,))
    eos_embedding = rng.uniform(-0.25, 0.25, (300,))
    unk_embedding = rng.uniform(-0.25, 0.25, (300,))
    word_vectors = [pad_embedding, sos_embedding, eos_embedding, unk_embedding]

    for word in total_word:
        try:
            word_vectors.append(model[word])  # 加载词向量
            word_dict.append(word)
        except KeyError:
            fail_word.append(word)

    word_vectors = np.array(word_vectors)
    word_dict = {word: index for index, word in enumerate(word_dict)}

    with open(final_vec_path, 'wb') as file:
        pickle.dump(word_vectors, file)

    with open(final_word_path, 'wb') as file:
        pickle.dump(word_dict, file)

    print("词典和词向量构建完成")


def get_index(type, text, word_dict):
    """
    得到词在词典中的位置。

    :param type: 文本类型（'code' 或 'text'）
    :param text: 输入文本
    :param word_dict: 词典
    :return: 词的位置列表
    """
    location = []
    if type == 'code':
        location.append(1)  # SOS
        for i in range(min(len(text), 348)):
            location.append(word_dict.get(text[i], word_dict['UNK']))
        location.append(2)  # EOS
    else:
        for word in text:
            location.append(word_dict.get(word, word_dict['UNK']))

    return location


def serialization(word_dict_path, type_path, final_type_path):
    """
    将训练、测试、验证语料序列化。

    :param word_dict_path: 词典文件路径
    :param type_path: 输入数据文件路径
    :param final_type_path: 序列化后的文件路径
    """
    with open(word_dict_path, 'rb') as f:
        word_dict = pickle.load(f)

    with open(type_path, 'r') as f:
        corpus = eval(f.read())

    total_data = []

    for data in corpus:
        qid, context, code, query, block_length, label = data[0], data[1], data[2], data[3], 4, 0

        Si_word_list = get_index('text', context[0], word_dict)
        Si1_word_list = get_index('text', context[1], word_dict)
        tokenized_code = get_index('code', code[0], word_dict)
        query_word_list = get_index('text', query, word_dict)

        Si_word_list = Si_word_list[:100] + [0] * (100 - len(Si_word_list))
        Si1_word_list = Si1_word_list[:100] + [0] * (100 - len(Si1_word_list))
        tokenized_code = tokenized_code[:350] + [0] * (350 - len(tokenized_code))
        query_word_list = query_word_list[:25] + [0] * (25 - len(query_word_list))

        one_data = [qid, [Si_word_list, Si1_word_list], [tokenized_code], query_word_list, block_length, label]
        total_data.append(one_data)

    with open(final_type_path, 'wb') as file:
        pickle.dump(total_data, file)

    print("序列化完毕")


if __name__ == '__main__':
    python_final_word_dict_path = '../hnn_process/ulabel_data/large_corpus/python_word_dict_final.pkl'
    new_python_large = '../hnn_process/ulabel_data/large_corpus/multiple/python_large_multiple_unlable.txt'
    large_python_f = '../hnn_process/ulabel_data/large_corpus/multiple/seri_python_large_multiple_unlable.pkl'

    serialization(python_final_word_dict_path, new_python_large, large_python_f)

    print('序列化完毕')
