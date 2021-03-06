# -*- coding: utf-8 -*-
"""Submission 2 - Multiple Parallel Time Series.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1L3uCPjtNMGQl-ZAFa3Ik7SFN73edlZ_Z

# **Configuration Colabs dan download dataset**
"""

from google.colab import drive
drive.mount('/content/drive')

import os
os.environ['KAGGLE_CONFIG_DIR'] = "/content/drive/My Drive/Dataset/Kaggle"

# Commented out IPython magic to ensure Python compatibility.
#changing the working directory
# %cd /content/drive/My Drive/Dataset/Kaggle

!kaggle datasets download -d nicholasjhana/energy-consumption-generation-prices-and-weather

!unzip energy-consumption-generation-prices-and-weather.zip -d '/content/drive/My Drive/Dicoding/Submission_2/dataset'

"""# **Import Library**"""

import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
import plotly.graph_objects as go

from livelossplot import PlotLossesKeras
from sklearn.preprocessing import MinMaxScaler
from keras.preprocessing.sequence import TimeseriesGenerator

"""# **Preparing Data**"""

dataset = '/content/drive/My Drive/Dicoding/Submission_2/dataset/energy_dataset.csv'
df = pd.read_csv(dataset)

display(df.head())
print(df.shape)

dates = pd.date_range(start='2015-01-01', end='2018-12-31 2300', freq='H')
df['time'] = pd.DatetimeIndex(dates).tz_localize('UTC').tz_convert('Europe/Madrid')
df = df.set_index('time')
df.head()

df.info()

df.isin([0]).sum()

"""Menghapus kolom yang memiliki nilai zero terbanyak dan nilai Nan. 
Serta menghapus nilai forecast yang telah dilakukan oleh penyedia data.
"""

df_new = df.drop(['generation hydro pumped storage aggregated', 'forecast wind offshore eday ahead', 
                     'generation fossil brown coal/lignite', 'generation fossil coal-derived gas', 
                     'generation fossil oil shale', 'generation fossil peat', 'generation geothermal', 
                     'generation hydro pumped storage consumption', 'generation marine', 
                     'generation wind offshore', 'forecast solar day ahead', 'forecast wind offshore eday ahead', 
                     'forecast wind onshore day ahead', 'total load forecast', 'price day ahead'], 
                    axis=1)

df_new.isnull().sum()

df_new.interpolate(method='linear', limit_direction='forward', inplace=True, axis=0)

df_new.isnull().sum()



"""# **Time Series Analysis**

## Visulization Original Data
"""

df_new[df_new.columns.to_list()].plot(subplots=True, figsize=(20, 12))
plt.show()

"""## Visualization 30Day Rolling"""

df_new = df_new.rolling('30D').mean()

df_new[df_new.columns.to_list()].plot(subplots=True, figsize=(20, 12))
plt.show()

"""## Melihat Korelasi antar kolom"""

correlations = df_new.corr(method='pearson') 
print(correlations['price actual'].sort_values(ascending=False).to_string())

col_del = correlations['price actual'].sort_values(ascending=False).index.to_list()[3:12]
# Menghapus Kolom yang nilai korelasinya kecil
df_new = df_new.drop(col_del, axis=1)

correlations = df_new.corr(method='pearson') 
print(correlations['price actual'].sort_values(ascending=False).to_string())

fig = go.Figure(data=go.Heatmap(
                    z=correlations,
                    x=correlations.index,
                    y=correlations.columns,
                    hoverongaps = False))
fig.show()



"""# **Split Data**"""

index_split = df_new.shape[0]*80//100

# Split Data
data_train = df_new[:index_split].values
data_test = df_new[index_split:].values

# Split Tanggal
date_train = df_new[:index_split].index
date_test = df_new[index_split:].index

"""Normalization"""

scaler_train = MinMaxScaler(feature_range=(0, 1))
scaler_test = MinMaxScaler(feature_range=(0, 1))

scaler_train.fit(data_train)
scaler_test.fit(data_test)

data_train_norm = scaler_train.transform(data_train)
data_test_norm = scaler_test.transform(data_test)

look_back = 15

train_generator = TimeseriesGenerator(data_train_norm, data_train_norm, length=look_back, batch_size=20)     
test_generator = TimeseriesGenerator(data_test_norm, data_test_norm, length=look_back, batch_size=1)



"""# **Build Model**"""

model = tf.keras.models.Sequential([
  tf.keras.layers.Bidirectional(
      tf.keras.layers.LSTM(100, return_sequences=True, activation='relu'), input_shape=(look_back,5)),
  tf.keras.layers.LSTM(50, activation='relu'),
  tf.keras.layers.Flatten(),
  tf.keras.layers.Dense(128, activation='relu'),
  tf.keras.layers.Dense(64, activation='relu'),
  tf.keras.layers.Dropout(0.1),
  tf.keras.layers.Dense(5)
])

loss = tf.keras.losses.Huber()
lr_schedule = tf.keras.callbacks.LearningRateScheduler(
              lambda epoch: 1e-4 * 10**(epoch / 10))

optimizer = tf.keras.optimizers.Adam(lr=6e-3, amsgrad=True)

model.compile(loss=loss, optimizer=optimizer, metrics=["mae"])

history = model.fit_generator(train_generator, epochs=10, 
                              callbacks=[lr_schedule, PlotLossesKeras()])

"""# **Evaluasi Model**"""

def mean_absolute_percentage_error(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.round(np.mean(np.abs((y_true - y_pred) / y_true)) * 100, 2)

prediction = model.predict_generator(test_generator)
pred = scaler_test.inverse_transform(prediction)

print('Mean Absolute Percetage Error : {}%'.format(mean_absolute_percentage_error(data_test[15:], pred)))



df_new.columns.to_list()

def plot_forecast(kolom, title):
  data_vis = go.Scatter(
    x = date_train,
    y = data_train[:, kolom],
    mode = 'lines',
    name = 'Data'
  )
  pred_vis = go.Scatter(
    x = date_test[15:],
    y = pred[:, kolom],
    mode = 'lines',
    name = 'Prediction'
  )
  test_vis = go.Scatter(
    x = date_test,
    y = data_test[:, kolom],
    mode='lines',
    name = 'True'
  )
  layout = go.Layout(
    title = title,
    xaxis = {'title' : "Time"},
    yaxis = {'title' : "Value"}
  )
  fig = go.Figure(data=[data_vis, pred_vis, test_vis], layout=layout)
  fig.show()

title = df_new.columns.to_list()
for i in range(len(title)):
  plot_forecast(i, title[i])