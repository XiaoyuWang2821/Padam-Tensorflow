from __future__ import absolute_import, division, print_function
import os
import sys
os.environ["CUDA_VISIBLE_DEVICES"]= sys.argv[1]
import tensorflow as tf
tf.enable_eager_execution()
import numpy as np
from keras.datasets import cifar10
import keras.callbacks as callbacks
import keras.utils.np_utils as kutils
from keras.preprocessing.image import ImageDataGenerator
from keras.utils import plot_model
from wide_resnet import WRNModel
from keras import backend as K
from padam import Padam
from amsgrad import AMSGrad

dataset = 'cifar10'
optimizer = 'adam'

if dataset == 'cifar10':
    MEAN = [0.4914, 0.4822, 0.4465]
    STD_DEV = [0.2023, 0.1994, 0.2010]
elif dataset == 'cifar100':
    MEAN = [0.507, 0.487, 0.441]
    STD_DEV = [0.267, 0.256, 0.276]


def preprocess(t):
    paddings = tf.constant([[2, 2,], [2, 2],[0,0]])
    t = tf.pad(t, paddings, 'CONSTANT')
    t = tf.image.random_crop(t, [32, 32, 3])
    t = normalize(t) 
    return t


def normalize(t):
    t = tf.div(tf.subtract(t, MEAN), STD_DEV) 
    return t

hyperparameters = {
    'cifar10': {
        'epoch': 200,
        'batch_size': 128,
        'decay_after': 50
    },
    'cifar100': {
        'epoch': 200,
        'batch_size': 128,
        'decay_after': 50  
    },
    'imagenet': {
        'epoch': 100,
        'batch_size': 256,
        'decay_after': 30
    }
}

optim_params = {
    'padam': {
        'weight_decay': 0.0005,
        'lr': 0.1,
        'p': 0.125,
        'b1': 0.9,
        'b2': 0.999
    },
    'adam': {
        'weight_decay': 0.0001,
        'lr': 0.001,
        'b1': 0.9,
        'b2': 0.99
    },
    'adamw': {
        'weight_decay': 0.025,
        'lr': 0.001,
        'b1': 0.9,
        'b2': 0.99
    },
    'amsgrad': {
        'weight_decay': 0.0001,
        'lr': 0.001,
        'b1': 0.9,
        'b2': 0.99
    },
    'sgd': {
        'weight_decay': 0.0005,
        'lr': 0.1,
        'm': 0.9
    }
}

hp = hyperparameters[dataset]
op = optim_params[optimizer]

if optimizer == 'adamw' and dataset=='imagenet':
    op['weight_decay'] = 0.05 

if dataset == 'cifar10':
    from keras.datasets import cifar10
    (trainX, trainY), (testX, testY) = cifar10.load_data()

elif dataset == 'cifar100':
    from keras.datasets import cifar100
    (trainX, trainY), (testX, testY) = cifar100.load_data()

batch_size = hp['batch_size']
img_rows, img_cols = 32, 32
epochs = hp['epoch']
train_size = trainX.shape[0]
print(train_size)

trainX = trainX.astype('float32')
trainX = trainX/255
testX = testX.astype('float32')
testX = testX/255
trainY = kutils.to_categorical(trainY)
testY = kutils.to_categorical(testY)

tf.train.create_global_step()

# base_learning_rate = 0.1


if optimizer is 'adamw':
	model = WRNModel(depth=16, multiplier=4, wd = 0)
else:
    model = WRNModel(depth=16, multiplier=4, wd = op['weight_decay'])

model._set_inputs(tf.zeros((batch_size, 32, 32, 3)))


learning_rate = tf.train.exponential_decay(op['lr'], tf.train.get_global_step() * batch_size,
                                       hp['decay_after']*train_size, 0.1, staircase=True)

if optimizer == 'padam':
    optim = Padam(learning_rate=learning_rate, p=op['p'], beta1=op['b1'], beta2=op['b2'])
elif optimizer == 'adam':
    optim = tf.train.AdamOptimizer(learning_rate=learning_rate, beta1=op['b1'], beta2=op['b2'])
elif optimizer == 'adamw':
    adamw = tf.contrib.opt.extend_with_decoupled_weight_decay(tf.train.AdamOptimizer)
    optim = adamw(weight_decay=op['weight_decay'], learning_rate=learning_rate,  beta1=op['b1'], beta2=op['b2'])
elif optimizer == 'amsgrad':
    optim = AMSGrad(learning_rate=learning_rate, beta1=op['b1'], beta2=op['b2'])
elif optimizer == 'sgd':
    optim = tf.train.MomentumOptimizer(learning_rate=learning_rate, momentum=op['m'])

loss = 'categorical_crossentropy'

model.compile(optimizer=optim, loss=loss,
                  metrics=['accuracy'], global_step=tf.train.get_global_step())

from keras.preprocessing.image import ImageDataGenerator

# Using zoom instead of : transforms.RandomCrop(32, padding=4)
datagen_train = ImageDataGenerator(zoom_range=0.125,
                            preprocessing_function=preprocess,
                            horizontal_flip=True,
                            )
datagen_test = ImageDataGenerator(
                            preprocessing_function=normalize,
                            )

model.fit_generator(datagen_train.flow(trainX, trainY, batch_size = batch_size), epochs = epochs, 
                                 validation_data = datagen_test.flow(testX, testY, batch_size = batch_size) , verbose=1)

scores = model.evaluate_generator(datagen_test.flow(testX, testY, batch_size = batch_size), verbose=1)
print("Final test loss and accuracy :", scores)


