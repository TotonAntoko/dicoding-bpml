# -*- coding: utf-8 -*-
"""Salinan dari Submission_3.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1shxnvmna0EggsOcISJ-FtRUZNnBh6tCc

# **Configuration Colabs and download dataset**
"""

from google.colab import drive
drive.mount('/content/drive')

import os
os.environ['KAGGLE_CONFIG_DIR'] = "/content/drive/My Drive/Dataset/Kaggle"

#changing the working directory
# %cd /content/drive/My Drive/Dataset/Kaggle

!kaggle datasets download -d alessiocorrado99/animals10

!unzip animals10.zip



"""# **Import Library**"""

# import os
# import cv2
import requests
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt

from PIL import Image
from io import BytesIO
# from tqdm.notebook import tqdm
from sklearn.model_selection import train_test_split

from tensorflow.keras import applications, optimizers
# from tensorflow.keras.models import Sequential, Model, load_model
from tensorflow.keras.preprocessing.image import ImageDataGenerator

tf.device('/device:GPU:0')

"""# **Visualisasi gambar acak setiap kategori¶**"""

fig, ax = plt.subplots(2, 5, figsize=(25,15))
fig.suptitle("Menampilkan satu gambar acak setiap kategori", fontsize=24)
data_dir = "raw-img/"
animals_sorted = sorted(os.listdir(data_dir))
animal_id = 0
for i in range(2):
  for j in range(5):
    try:
      animal_selected = animals_sorted[animal_id] 
      animal_id += 1
    except:
      break
    if animal_selected == '.TEMP':
        continue
    animal_selected_images = os.listdir(os.path.join(data_dir,animal_selected))
    animal_selected_random = np.random.choice(animal_selected_images)
    img = plt.imread(os.path.join(data_dir,animal_selected, animal_selected_random))
    ax[i][j].imshow(img)
    ax[i][j].set_title(animal_selected, pad = 10, fontsize=22)
    
plt.setp(ax, xticks=[],yticks=[])
plt.tight_layout()

"""# **Preparing Data**"""

kategori_dict = {"cane": "Dog", "cavallo": "Horse", "elefante": "Elephant", 
             "farfalla": "Butterfly", "gallina": "Chicken", "gatto": "Cat", 
             "mucca": "Cow", "pecora": "Sheep", "scoiattolo": "Squirrel", "ragno": "Spider"}

# Membuat Dataframe
foldernames = os.listdir('raw-img/')
path_get, path_not, kategori_get, kategori_not = [], [], [], []

for i, folder in enumerate(foldernames):
    filenames = os.listdir("raw-img/" + folder);
    count = 0
    for file in filenames:
        if count < 3000: # Mengambil 3000 data max tiap kategori
            path_get.append("raw-img/" + folder + "/" + file)
            kategori_get.append(kategori_dict[folder])
        # else:
        #     path_not.append("raw-img/" + folder + "/" + file)
        #     kategori_not.append(kategori_dict[folder])
        count += 1

df = pd.DataFrame({'path':path_get, 'kategori':kategori_get})
# dft = pd.DataFrame({'path':path_not, 'kategori':kategori_not})
train, test = train_test_split(df, test_size=0.2, random_state = 0)

train_gen = ImageDataGenerator(rescale=1./255,
  shear_range=0.3,
  zoom_range=0.3,
  horizontal_flip=True,
  rotation_range=35, 
  width_shift_range=0.15,
  height_shift_range=0.15,
  samplewise_center = True,
)

test_gen = ImageDataGenerator(rescale=1./255, samplewise_center = True)

train_flow = train_gen.flow_from_dataframe(
    train, x_col = 'path', 
    y_col = 'kategori', 
    target_size=(224, 224),  
    validate_filenames = False,
    class_mode='categorical', 
    batch_size=64)
test_flow = test_gen.flow_from_dataframe(
    test, x_col = 'path', 
    y_col = 'kategori', 
    target_size=(224, 224), 
    validate_filenames = False,
    class_mode='categorical', 
    batch_size=64)

model = tf.keras.models.Sequential([
                                    
  applications.ResNet152V2(weights="imagenet", include_top=False, 
                           input_tensor=tf.keras.layers.Input(shape=(224, 224, 3))),

  tf.keras.layers.MaxPooling2D(pool_size=(6, 6)),

  tf.keras.layers.Convolution2D(2048, 1, 1),
  tf.keras.layers.Activation('relu'),
  tf.keras.layers.MaxPooling2D(pool_size=(1, 1)),
  
  tf.keras.layers.Convolution2D(1024, 1, 1),
  tf.keras.layers.Activation('relu'),
  tf.keras.layers.MaxPooling2D(pool_size=(1,1)),

  tf.keras.layers.Convolution2D(512, 1, 1),
  tf.keras.layers.Activation('relu'),
  tf.keras.layers.MaxPooling2D(pool_size=(1,1)),

  tf.keras.layers.Convolution2D(256, 1, 1),
  tf.keras.layers.Activation('relu'),
  tf.keras.layers.MaxPooling2D(pool_size=(1,1)),

  tf.keras.layers.Convolution2D(128, 1, 1),
  tf.keras.layers.Activation('relu'),
  tf.keras.layers.MaxPooling2D(pool_size=(1,1)),

  tf.keras.layers.Convolution2D(64, 1, 1),
  tf.keras.layers.Activation('relu'),
  tf.keras.layers.MaxPooling2D(pool_size=(1,1)),

  tf.keras.layers.Flatten(), 
  tf.keras.layers.Dropout(0.2),
  tf.keras.layers.Dense(256, activation='relu'),
  tf.keras.layers.Dropout(0.2),
  tf.keras.layers.Dense(10, activation='softmax')  
])
model.layers[0].trainable = False

def scheduler(epoch, lr):
  if epoch < 5:
    return lr
  else:
    return lr * tf.math.exp(-0.1)

lr_schedule = tf.keras.callbacks.LearningRateScheduler(scheduler, verbose=1)
tb_callback = tf.keras.callbacks.TensorBoard(
    log_dir='logs', histogram_freq=0, write_graph=True, write_images=False,
    update_freq='epoch', embeddings_freq=0,
    embeddings_metadata=None
)

model.compile(loss = 'categorical_crossentropy', optimizer = optimizers.SGD(lr=1e-3, momentum=0.9), 
              metrics = ['accuracy'])
model.summary()

with tf.device("/device:GPU:0"):
  history = model.fit_generator(train_flow, epochs = 15, validation_data = test_flow, 
                                steps_per_epoch=train.shape[0]//224, validation_steps=test.shape[0]//224,
                                callbacks=[lr_schedule, tb_callback])

# Evaluasi Model
eval_model = model.evaluate_generator(test_flow, verbose=1)
print('Loss : {} \nAcc : {}'.format(eval_model[0]*100, eval_model[1]*100))

# Commented out IPython magic to ensure Python compatibility.
# Load the TensorBoard notebook extension.
# %load_ext tensorboard
# %tensorboard --logdir logs

"""# Predict Data"""

def predict_class(model, images, show = True):
  !mkdir image_predict
  for i in range(len(images)):
    Image.open(BytesIO(requests.get(images[i]).content)).save(
        '/content/image_predict/' + str(i) + '.png')

  rows,cols = ((len(images) - 1) // 5 ) + 1,5
  temp_axis = rows * 4
  fig, axes = plt.subplots(nrows=rows, ncols=cols, figsize=(15,temp_axis))
  for i, img in enumerate(images):
    img = tf.keras.preprocessing.image.load_img(
        '/content/image_predict/' + str(i) + '.png', target_size=(224, 224))
    img = tf.keras.preprocessing.image.img_to_array(img)                    
    img = np.expand_dims(img, axis=0)         
    img /= 255.                                      

    pred = model.predict(img)
    index = np.argmax(pred)
    pred_value = list(train_flow.class_indices.keys())[index]
    if show:
      axes[i//cols, i%cols].set_title(pred_value)
      axes[i//cols, i%cols].axis('off')
      axes[i//cols, i%cols].imshow(img[0])

images = ['https://pbs.twimg.com/profile_images/378800000532546226/dbe5f0727b69487016ffd67a6689e75a.jpeg',
           'https://i.ytimg.com/vi/UwtTSqTbWzg/maxresdefault.jpg',
           'https://images.unsplash.com/photo-1547399300-7613d8f5f8f1?ixlib=rb-1.2.1&w=1000&q=80',
           'https://www.theartofdoingstuff.com/wp-content/uploads/2014/06/Studio_BlkCpMrnHn_8771_L2.jpg',
           'https://www.k9rl.com/wp-content/uploads/2017/01/Tibetan-Spaniel-dog.jpg',
           'https://static.boredpanda.com/blog/wp-content/uploads/2016/06/I-found-freedom-with-horses-576d2d0804976__880.jpg',
           'https://th.bing.com/th/id/OIP.tOb0fbG7VgjMf2Mj7Sa9igHaEK?pid=Api&rs=1',
           'https://pixfeeds.com/images/topic/2779/1200-2779-butterflies-photo1.jpg',
           'https://th.bing.com/th/id/OIP.GmYkDxsD--csxHFes-lWFwHaDS?pid=Api&rs=1',
           'https://resize.hswstatic.com/w_1024/gif/banana-spider.jpg',
           'https://www.nationalgeographic.com/content/dam/animals/2018/10/waq-animal-caches/01-waq-animal-caches-nationalgeographic_1902487.ngsversion.1539338405615.adapt.1900.1.jpg',
           'https://upload.wikimedia.org/wikipedia/commons/a/ac/Bombay_femelle.JPG',
           'https://th.bing.com/th/id/OIP.1L_D_VUm0lIxk_g1-5uxrgHaEi?pid=Api&rs=1',
           'https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/7_month_old_Suffolk_Ram_Lamb.JPG/1200px-7_month_old_Suffolk_Ram_Lamb.JPG',
           'https://www.guidedogs.org/wp-content/uploads/2019/11/website-donate-mobile.jpg',
           'https://kids.sandiegozoo.org/sites/default/files/2017-09/animal-hero-spiders.jpg',
           'https://media4.s-nbcnews.com/j/newscms/2014_11/241886/140310-smart-elephants-347_5f910b48b8c1a85fc892e9c3d9cc2d00.fit-760w.jpg',
           'https://rollingharbourlife.files.wordpress.com/2013/05/squirrel-nyc-3.jpg',
           'https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/African_Bush_Elephant.jpg/250px-African_Bush_Elephant.jpg',
           'https://i.imgur.com/drfirIW.jpg'
          ]
predict_class(model, images, True)

"""# Simpan Model dalam TF-Lite"""

# Konversi model.
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

with tf.io.gfile.GFile('model.tflite', 'wb') as f:
  f.write(tflite_model)