import numpy as np
import pandas as pd
from konlpy.tag import Okt
from gensim import models
import matplotlib.pyplot as plt
import os
from tensorflow import keras
import pickle

max_len = 30

def preprocessing(data):
    data.drop_duplicates(subset=['document'], inplace=True)
    data = data.dropna(how = 'any')
    data['document'] = data['document'].str.replace("[^ㄱ-ㅎㅏ-ㅣ가-힣 ]","")
    data['document'].replace('', np.nan, inplace=True)
    data = data.dropna(how = 'any')
    sentences = data['document'].tolist()
    label = data['label']
    print('data len = {}'.format(len(sentences)))
    return sentences, label

def tokenize(sentence):
    okt = Okt()
    tokenized_sentence = []

    # 우선 단어의 기본형으로 모두 살리고, 명사, 동사, 영어만 담는다.
    # 그냥 nouns로 분리하는 것보다 좀 더 정확하고 많은 데이터를 얻을 수 있다.
    for line in sentence:
        result = []
        temp_sentence = okt.pos(line, norm=True, stem=True) # 먼저 형태소 분리해서 리스트에 담고

        for i in temp_sentence:                             
            if (i[1] == 'Noun' or i[1] == 'Adjective' or i[1] == 'Alpha'):                  
                result.append(i[0])
            
        tokenized_sentence.append(result)

    return tokenized_sentence

def pad_sequence(sentences, padding_word="<PAD/>", max_len=max_len): #  오른쪽을 패딩주기
    max_len = max_len
    padded_sentences = []
    for i in range(len(sentences)):
        sentence = sentences[i]
        if len(sentence)<=max_len:
            num_padding = max_len - len(sentence)
            new_sentence = sentence + [padding_word] * num_padding
        else : new_sentence = sentence[:max_len]
        padded_sentences.append(new_sentence)
    return padded_sentences

def fasttext_vectorize(padded_sentences, max_len = max_len):
    ko_model = models.fasttext.load_facebook_model('cc.ko.300.bin')
    paddedarray = np.array([ko_model.wv.word_vec(token) for x in padded_sentences for token in x])
    final_array = paddedarray.reshape(-1,max_len,300)
    return final_array

def simple_fasttext_vectorize(padded_sentences, max_len = max_len):
    with open('simple_ko_vec.pkl','rb') as fw:
        simple_w2v= pickle.load(fw)
    paddedarray=[]
    try:
        for x in padded_sentences:
            for token in x:
                paddedarray.append(simple_w2v[token])
        # paddedarray = np.array([simple_w2v[token] for x in padded_sentences for token in x])
    except:
        paddedarray.append(simple_w2v['얘쁜'])## 사전에 없는 단어는 0행렬 만듬 ['얘쁜']의 행렬이 0행렬이라 이렇게 그냥 썼음
    paddedarray = np.array(paddedarray)
    final_array = paddedarray.reshape(-1,max_len,300)
    return final_array

def plot_graphs(history, string, name='model'):
    plt.plot(history.history[string])
    plt.plot(history.history['val_' + string])
    plt.xlabel("Epochs")
    plt.ylabel(string)
    plt.title(name)
    plt.legend([string, 'val_' + string])
    
    ##저장될 폴더생성
    result_dir = './result_file'
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    plt.savefig(result_dir+'/{}.png'.format(name))
    plt.show() #결과 그냥 저장할거라 주석처리해도됨
    print('<{}.png> result_file폴더에 결과 그래프 저장 완료'.format(name))


######################################
#######  model1:fastext이용 ###########
###################################### 
def CNN_model_1(num_filters=100, hidden_dims = 10, filter_sizes = (3, 4, 5), l2_norm = 0.003):
    # embedding_dim = 200
    filter_sizes = filter_sizes
    num_filters = num_filters
    dropout = 0.5
    hidden_dims = hidden_dims
    # batch_size = 50
    # num_epochs = 10
    conv_blocks = []
    # sequence_length = 200
    l2_norm = l2_norm

# input_shape = (sequence_length, embedding_dim) # input shape for
    input_shape = (max_len, 300) # input shape for data, (max_length of sent, vect)

    model_input = keras.layers.Input(shape=input_shape)

    z = model_input
    for sz in filter_sizes:
        conv = keras.layers.Conv1D(filters=num_filters,
                            kernel_size=sz,
                            padding="valid",
                            activation="relu",
                            strides=1)(z)
        conv = keras.layers.MaxPooling1D(pool_size=2)(conv)
        conv = keras.layers.Flatten()(conv)
        conv_blocks.append(conv)
    z = keras.layers.Concatenate()(conv_blocks) if len(conv_blocks) > 1 else conv_blocks[0]
    z = keras.layers.Dense(hidden_dims, activation="relu", kernel_regularizer=keras.regularizers.l2(l2_norm), bias_regularizer=keras.regularizers.l2(l2_norm))(z)
    z = keras.layers.Dropout(dropout)(z)
    model_output = keras.layers.Dense(1, activation="sigmoid")(z)

    model = keras.Model(model_input, model_output)
    model.compile(loss="binary_crossentropy", optimizer="adam", metrics=["accuracy"])
    # Create a new linear regression model.
    # model = keras.Sequential([keras.layers.Dense(1)])
    # model.compile(optimizer='adam', loss='mse')


    return model 