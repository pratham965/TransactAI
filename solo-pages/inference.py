threshold = 0.019621696
import  tensorflow as tf
model = tf.keras.models.load_model("/content/model_best.keras")
reconstcution_a=model.predict(df_fraud)
reconstruction_a = np.array(reconstcution_a, dtype=np.float32)
df_fraud = np.array(df_fraud, dtype=np.float32)
test_loss=tf.keras.losses.mae(reconstruction_a,df_fraud)
tf.math.less(test_loss,threshold)