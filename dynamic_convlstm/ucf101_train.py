import sys
import os
import numpy as np
import tensorflow as tf
from config import FLAGS
from model import DynamicRNN

video_label = []
with open('../data/ucfTrainTestlist/trainlist01.txt', 'r') as f:
  for line in f:
    video_info, class_id = line.split()
    _, video_name = video_info.split('/')
    video_label.append((video_name.strip(), int(class_id) - 1)) 

FEATURE_HOME = '../feature-extraction/ucf101-block4-7-7-2048-features'
dataset = []
for video_name, class_id in video_label:
  video_feature_name = video_name.split('.')[0] + '.npy'
  video_feature_path = os.path.join(FEATURE_HOME, video_feature_name)
  video_feature = np.load(video_feature_path)
  dataset.append((video_feature, class_id))

training_steps_per_epoch = len(dataset) // FLAGS.batch_size
model = DynamicRNN(feature_side=FLAGS.feature_side,
                   feature_size=FLAGS.feature_size,
                   num_layers=FLAGS.num_layers,
                   max_video_length=FLAGS.max_video_length,
                   num_classes=FLAGS.num_classes,
                   convlstm_output_channels=FLAGS.convlstm_output_channels,
                   convlstm_kernel_shape=[FLAGS.convlstm_kernel_side, FLAGS.convlstm_kernel_side],
                   conv_output_channels=FLAGS.conv_output_channels,
                   conv_kernel_shape=[FLAGS.conv_kernel_side, FLAGS.conv_kernel_side],
                   learning_rate=FLAGS.learning_rate,
                   learning_rate_decay_factor=FLAGS.learning_rate_decay_factor,
                   min_learning_rate=FLAGS.min_learning_rate,
                   training_steps_per_epoch=training_steps_per_epoch,
                   max_gradient_norm=FLAGS.max_gradient_norm,
                   keep_prob=FLAGS.keep_prob,
                   input_keep_prob=FLAGS.input_keep_prob,
                   output_keep_prob=FLAGS.output_keep_prob,
                   state_keep_prob=FLAGS.state_keep_prob,
                   is_training=True)

with tf.Session() as sess:
  ckpt = tf.train.get_checkpoint_state(FLAGS.checkpoint_dir)
  if ckpt and tf.train.checkpoint_exists(ckpt.model_checkpoint_path):
    print("Reading model parameters from %s" % ckpt.model_checkpoint_path)
    model.saver.restore(sess, ckpt.model_checkpoint_path)
    step = int(ckpt.model_checkpoint_path.split('-')[1])
  else:
    sess.run(tf.global_variables_initializer())
    step = 0

  zero_pad = np.zeros((FLAGS.feature_side, FLAGS.feature_side, FLAGS.feature_size))

  for epoch in range(1, FLAGS.num_epochs+1):
    np.random.shuffle(dataset)
    for start, end in zip(range(0, len(dataset), FLAGS.batch_size), range(FLAGS.batch_size, len(dataset), FLAGS.batch_size)):
      batch_feature = []
      batch_label = []
      batch_length = []
      for i in range(start, end):
        feature, label = dataset[i]
        batch_label.append(label)
        batch_length.append(feature.shape[0])
        pad = np.stack([zero_pad]*(FLAGS.max_video_length-feature.shape[0]))
        feature = np.concatenate((feature, pad), axis=0)
        batch_feature.append(feature)
      feed_dict = {model.frame_feature_ph: batch_feature, model.video_length_ph:batch_length, model.video_label_ph:batch_label}
      loss, learning_rate, _ = sess.run([model.loss, model.learning_rate, model.train_op], feed_dict=feed_dict)
      step += 1
      if step % FLAGS.steps_per_checkpoint == 0:
        checkpoint_path = os.path.join(FLAGS.checkpoint_dir, "ckpt")
        model.saver.save(sess, checkpoint_path, global_step=model.global_step)
      print "%5d: %.6f\t%.6f"%(step, learning_rate, loss)
      sys.stdout.flush()
