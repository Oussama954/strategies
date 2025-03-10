# Neural Network Trinary Classifier: this subclass uses a full size Wavenet model

# code influenced by: https://github.com/basveeling/wavenet/blob/bf8ef958372692ecb32e8540f7c81f69a186eb8d/wavenet.py#L20


import numpy as np
from pandas import DataFrame, Series
import pandas as pd

pd.options.mode.chained_assignment = None  # default='warn'

# Strategy specific imports, files must reside in same folder as strategy
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import logging
import warnings

log = logging.getLogger(__name__)
# log.setLevel(logging.DEBUG)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

import random

import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1'
os.environ['TF_DETERMINISTIC_OPS'] = '1'

import tensorflow as tf

seed = 42
os.environ['PYTHONHASHSEED'] = str(seed)
random.seed(seed)
tf.random.set_seed(seed)
np.random.seed(seed)

tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.WARN)

import keras
from keras import layers
from ClassifierKerasTrinary import ClassifierKerasTrinary

from keras.layers import Convolution1D
from keras.regularizers import l2

import h5py


class NNTClassifier_Wavenet2(ClassifierKerasTrinary):
    is_trained = False
    clean_data_required = False  # training data cannot contain anomalies

    def wavenetBlock(self, n_filters, filter_size, rate):
        def f(input_):
            residual = input_
            tanh_out = layers.Convolution1D(n_filters, filter_size, padding="causal", dilation_rate=rate,
                                            activation='tanh')(input_)
            sigmoid_out = layers.Convolution1D(n_filters, filter_size, padding="causal", dilation_rate=rate,
                                               activation='sigmoid')(input_)
            merged = layers.Multiply()([tanh_out, sigmoid_out])

            # skip_x = layers.Convolution1D(nb_filters, 1, padding='same', use_bias=use_bias,
            #                               kernel_regularizer=l2(res_l2))(x)
            # res_x = layers.Add()([residual, res_x])
            #
            # skip_out = layers.Convolution1D(n_filters, 1, padding='same')(merged)
            # out = layers.Add()([skip_out, residual])
            # return out, skip_out

            x = layers.Multiply()([tanh_out, sigmoid_out])

            res_x = layers.Convolution1D(n_filters, 1, padding='same', kernel_regularizer=l2(0))(x)
            skip_x = layers.Convolution1D(n_filters, 1, padding='same', kernel_regularizer=l2(0))(x)
            res_x = layers.Add()([input_, res_x])
            return res_x, skip_x

        return f

    # override the build_model function in subclasses
    def create_model(self, seq_len, num_features):

        # model = keras.Sequential(name=self.name)
        inputs = layers.Input(shape=(seq_len, num_features))

        # x = inputs
        x = layers.Convolution1D(64, 2, padding="causal", dilation_rate=1)(inputs)

        # A, B = self.wavenetBlock(64, 2, 1)(inputs)

        skip_connections = []
        for i in range(1, 3):
            rate = 1
            for j in range (1, 10):
                x, skip = self.wavenetBlock(64, 2, rate)(x)
                skip_connections.append(skip)
                rate = 2 * rate

            x = layers.BatchNormalization()(x)

        x = layers.Add()(skip_connections)
        x = layers.Activation('relu')(x)
        x = layers.Convolution1D(64, 1, padding='same', kernel_regularizer=l2(0))(x)
        x = layers.Activation('relu')(x)
        x = layers.Convolution1D(64, 1, padding='same')(x)

        # last layer is a trinary decision - do not change
        outputs = layers.Dense(3, activation="softmax")(x)

        model = keras.Model(inputs, outputs)

        return model
